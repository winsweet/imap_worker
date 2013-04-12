import mailbox
import getpass
import sys
import os
import time

MBOXES_DIR = 'mboxes'
ATTACHMENTS_DIR = 'files'
ONE_DAY_AND_ONE_MINUTE = 24 * 60 * 60 + 60 # one day and one minute in seconds
NUMBER_OF_USERS = 25000
MAX_MSG_NUMBER = 25
PERCENT_OF_EMAILS_WITH_ATTACHMENT = 0.2 # 20%

def create_email(to_addr, from_addr, subject, body, filename=None):
    """
    """
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    from email.mime.multipart import MIMEMultipart

    msg = MIMEMultipart()
    msg['To'] = to_addr
    msg['From'] = from_addr
    msg['Subject'] = subject

    if filename:
        image = MIMEImage(open(filename, 'rb').read())
        image.add_header('Content-Disposition', 'attachment', filename=os.path.basename(filename))
        msg.attach(image)

    msg.attach(MIMEText(body, 'plain'))

    return msg.as_string()

def create_mailbox(filename, msg_list):
    """
    """
    mbox = mailbox.mbox(filename)
    for msg in msg_list:
        mbox.add(msg)
    mbox.flush()
    mbox.close()

def worker(user, password):
    """
    Send one mbox and sleep due to gmail restrictions
    """
    if os.path.exists(MBOXES_DIR):
        for mbox in sorted(os.listdir(MBOXES_DIR)):
            path = os.path.join(MBOXES_DIR, mbox)
            print 'Upload', path, 'mailbox ...'
            upload_mailbox(path, user, password)
            time.sleep(ONE_DAY_AND_ONE_MINUTE)
        os.rmdir(MBOXES_DIR)
        sys.exit(0)

def upload_mailbox(filename, user, password):
    """
    """
    import subprocess as sp

    error_filename = '%s.err' % filename
    cmd = 'python imap_upload.py --gmail --box=test --user=' + user + ' --password=' + password + 
        ' --error=' + error_filename + ' ' + filename

    p = sp.Popen(cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    (stdoutdata, stderrdata) = p.communicate()

    if os.path.exists(error_filename):
        st = os.stat(error_filename)
        if st.st_size == 0:
            os.remove(error_filename)

    if p.returncode == 0 and os.path.exists(filename):
        os.remove(filename)

    if p.returncode and os.path.exists(error_filename):
        os.remove(filename)
        os.rename(error_filename, filename)

if __name__ == '__main__':
    from optparse import OptionParser

    usage = 'usage: %prog [-d dir] [-n N] -u USER [-p PASSWORD]'
    parser = OptionParser(usage)

    parser.add_option('-d', '--dir',
        action='store',
        type='string',
        dest='dir',
        metavar='DIR',
        help='dir with EML emails')

    parser.add_option('-n', '--num-emails',
        action='store',
        type='int',
        dest='num_emails',
        metavar='EMAILS',
        default=80,
        help='number of emails per day (default is 80)')

    parser.add_option('-u', '--user',
        action='store',
        type='string',
        dest='user',
        metavar='USER',
        help='gmail account username')

    parser.add_option('-p', '--password',
        action='store',
        type='string',
        dest='password',
        metavar='PASSWORD',
        help='gmail account password')

    (options, args) = parser.parse_args()

    if not options.user:
        parser.print_help()
        sys.exit(1)

    if not options.password:
        options.password = getpass.getpass()

    worker(options.user, options.password)

    os.mkdir(MBOXES_DIR)
    if options.dir:
        # create mbox'ex from dir 
        msg_list = []
        i = 0
        n = 1
        listdir = os.listdir(options.dir)
        for eml in listdir:
            path = os.path.join(options.dir, eml)
            msg_list.append(open(path).read())
            i += 1
            if i == options.num_emails or i == len(listdir):
                filename = os.path.join(MBOXES_DIR, '%04d' % n)
                print 'Create', filename, 'mailbox ...'
                create_mailbox(filename, msg_list)
                i = 0
                msg_list = []
                n += 1
    else:
        # generate emails and mbox'es
        import random
        data = []
        for user_id in xrange(1, NUMBER_OF_USERS + 1):
            for msg_id in xrange(1, random.randint(1, MAX_MSG_NUMBER)):
                data.append(dict(user_id=user_id, msg_id=msg_id))

        emails_with_attachment = int(round(len(data) * PERCENT_OF_EMAILS_WITH_ATTACHMENT))

        files = os.listdir(ATTACHMENTS_DIR)
        i = 0
        while i < emails_with_attachment:
             d = random.choice(data)
             if not 'attachment' in d:
                 d['attachment'] = os.path.join(ATTACHMENTS_DIR, random.choice(files))
                 i += 1

        msg_list = []
        i = 0
        n = 1
        for d in data:

            to_addr = options.user
            from_addr = 'a%08d@babycarrot.sg' % d['user_id']
            subject = 'from %s to gmail msg %d' % (from_addr, d['msg_id'])
            body = subject

            if 'attachment' in d:
                msg = create_email(to_addr, from_addr, subject, body, filename=d['attachment'])
            else:
                msg = create_email(to_addr, from_addr, subject, body)

            msg_list.append(msg)

            i += 1
            if i == options.num_emails or i == len(data):
                filename = os.path.join(MBOXES_DIR, '%04d' % n)
                print 'Create', filename, 'mailbox ...'
                create_mailbox(filename, msg_list)
                i = 0
                msg_list = []
                n += 1

    worker(options.user, options.password)
