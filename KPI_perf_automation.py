#!/usr/bin/python
import logging
import subprocess
from pathlib import Path
import os
import time
import glob
import shutil
import sys
import requests


# Custom logger
logger = logging.getLogger()


# Handler
handler = logging.StreamHandler()
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


# Jmeter version
jmeter_base_path = "/home/apache-jmeter-4.0/bin"
# jmeter_base_path = "/home/apache-jmeter-5.1.1/bin"


# Paths
jtl_path = "{base}/jtl".format(base=jmeter_base_path)
properties_path = "{base}/properties/".format(base=jmeter_base_path)

# CPI/BAE Logins
cpi_user = "root"
cpi_host = input("Enter CPI/BAE host. (Example: vmr-cpi-0034) :")
cpi_metrics_path = "/var/opt/log/bae/Metrics.log"
cpi_metrics_file = "Metrics.log"


def properties_list():
    plist = [os.path.basename(x) for x in glob.glob(properties_path + "*.properties")]
    plist.sort()
    logger.debug(plist)
    logger.debug("Starting test. See debug.log for details\n")
    for f in plist:
        logger.info('\x1b[6;30;43m' + 'Starting {file} test'.format(file=f) + '\x1b[0m')
        run_jmeter(f, "{jtl}/{file}".format(jtl=jtl_path, file=f))
    check_errors()
    logger.info('\x1b[6;30;42m' + 23*'-' + 'End of test' + 23*'-' + '\x1b[0m')


def clear_jtl():
    logger.debug("Clear JTL files from jmeter.")
    cmd_jtl = "rm -f {base}/*.jtl".format(base=jtl_path)
    os.system(cmd_jtl)
    logger.info("JTL files removed!")


def check_errors():
    logger.debug("Finding for errors on jtl results files.")
    logger.info('\x1b[6;30;43m' + 23*'*' + '  CHECK THE FOLLOWING FILES FOR ERRORS  ' + 23*'*' + '\x1b[0m')
    cmd_find = "find {base} -type f -size +85c -iname ViewResultsTree.jtl".format(base=jtl_path)
    os.system(cmd_find)


def run_jmeter(file, output_dir):
    global result_dir
    global file_global
    result_dir = output_dir
    file_global = file

    os.system("sh {base}/jmeter.sh -n ".format(base=jmeter_base_path) +
              "-t {base}/AEL.jmx ".format(base=jmeter_base_path) +
              "-q {base}{property_file}".format(base=properties_path, property_file=file))
    logger.info("Thread finished. Shutting down Jmeter...\n")
    time.sleep(5)
    logger.debug("Sending stoptest to Jmeter...\n")
    os.system("sh {base}/stoptest.sh".format(base=jmeter_base_path))
    time.sleep(0)
    logger.debug("Jmeter --PROBABLY-- down...\n")

# Save files
    create_folder()
    get_metrics()
    move_files()

# Clear karaf counters
    karaf_clear()
    logger.info("Starting next thread group...\n")
    time.sleep(5)


def create_folder():
    logger.debug("Creating folder for JTL files...\n")
    try:
        if os.path.exists(os.path.dirname("{base}/{new}/".format(base=jtl_path, new=file_global))):
            logger.debug("Removing old folder..." + "{base}/{new}/".format(base=jtl_path, new=file_global))
            shutil.rmtree(os.path.dirname("{base}/{new}/".format(base=jtl_path, new=file_global)))
            logger.debug("Old folder removed..creating a new one...")
            os.mkdir("{base}/{new}".format(base=jtl_path, new=file_global))
            logger.debug("Folder " + "{base}/{new}/".format(base=jtl_path, new=file_global) + "created!")
        else:
            logger.debug("Creating a new folder...")
            os.mkdir("{base}/{new}".format(base=jtl_path, new=file_global))
            logger.debug("Folder " + "{base}/{new}/".format(base=jtl_path, new=file_global) + "created!")
    except OSError as err:
        print(err)


def get_metrics():
    logger.info("Get metrics.log from BAE VM...\n")
    os.system(
        "sftp -o 'StrictHostKeyChecking no' -o 'LogLevel=error' {user}@{host}".format(user=cpi_user, host=cpi_host) +
        ":{metrics} ".format(metrics=cpi_metrics_path) +
        "{base}/{new}/{metrics_file}".format(base=jtl_path, new=file_global, metrics_file=cpi_metrics_file))


def move_files():
    logger.info("Moving JTL to new folder...\n")
    source = os.listdir(jtl_path)
    for files in source:
        if files.endswith(".jtl"):
            shutil.move(os.path.join(jtl_path, files), result_dir)
            logger.debug("file " + (os.path.join(jtl_path, files) + " moved!!"))


def ask_user():
    check = str(input("Are you sure to run this script ? (Y/N): ")).lower().strip()
    try:
        if check[0] == 'y':
            exchange_key()
            change_bae_log_level()
            properties_list()
        elif check[0] == 'n':
            exit(0)
        else:
            print('Invalid Input')
            return ask_user()
    except Exception as error:
        print("Please enter valid inputs")
        print(error)
        return ask_user()


def ask_user_jtl():
    check = str(input("Do you want to remove JTL files from jmeter machine? (Y/N): ")).lower().strip()
    try:
        if check[0] == 'y':
            clear_jtl()
            ask_user()
        elif check[0] == 'n':
            ask_user()
        else:
            print('Invalid Input')
            return ask_user_jtl()
    except Exception as error:
        print("Please enter valid inputs")
        print(error)
        return ask_user_jtl()


def karaf_clear():
    logger.info("Clear karaf timers and gauges...\n")
    sshprocess = subprocess.Popen(['ssh', '-o', 'LogLevel=error', '{user}@{host}'.format(user=cpi_user, host=cpi_host)],
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  universal_newlines=True,
                                  bufsize=0)

    logger.debug("Clearing timers....\n")
    sshprocess.stdin.write("ssh -tto 'StrictHostKeyChecking no' -o 'LogLevel=error'"
                           " localhost -p 13122 "'aep-metrics:mcleartimers -r'"\n")

    logger.debug("Clearing gauges....\n")
    sshprocess.stdin.write("ssh -tto 'StrictHostKeyChecking no' -o 'LogLevel=error'"
                           " localhost -p 13122 "'aep-metrics:mcleargauges -r'"\n")
    sshprocess.stdin.write("echo END\n")
    sshprocess.stdin.close()

    for line in sshprocess.stdout:
        if line == "END\n":
            break
        print(line, end="")

    for line in sshprocess.stdout:
        if line == "END\n":
            break
        print(line, end="")


def exchange_key():
    logger.info("Exchanging keys with BAE machine.")

    logger.debug("Remove BAE key from host.")
    os.system('ssh-keygen -R {user}@{host}'.format(user=cpi_user, host=cpi_host))

    logger.debug("Copy key to BAE host.")
    os.system('ssh-copy-id -i ~/.ssh/id_rsa -o LogLevel=error {user}@{host}'.format(user=cpi_user, host=cpi_host))

    karaf_clear()


def change_bae_log_level():
    logger.debug("Changing BAE instance log level to ERROR...\n")
    sshprocess = subprocess.Popen(['ssh', '-o', 'LogLevel=error', "{user}@{host}".format(user=cpi_user, host=cpi_host)],
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  universal_newlines=True,
                                  bufsize=0)

    sshprocess.stdin.write(
        "sudo sed -i -e \'s/<logger name=\"com.ericsson.bss.ael.bae\" level=[^ ]* /<logger "
        "name=\"com.ericsson.bss.ael.bae\" level=\"ERROR\" /\' -e \'s/<logger name=\"com.ericsson.bss.ael.aep\" "
        "level=[^ ]* /<logger name=\"com.ericsson.bss.ael.aep\" level=\"ERROR\" "
        "/\' /opt/osgi/apache-custom-karaf-4.1.4/instances/bae/etc/logback.xml")

    logger.info("BAE log level was set to ERROR!\n")
    control_instance()


def control_instance():
    logger.info("Restarting BAE instance")
    sshprocess = subprocess.Popen(
        ['ssh', '-o', 'LogLevel=error', "{user}@{host}".format(user=cpi_user, host=cpi_host)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=0)
    sshprocess.stdin.write("/opt/bae/karaf/bin/ctrl_bae_instance restart && sleep 10\n")
    sshprocess.stdin.write("/opt/bae/karaf/bin/ctrl_bae_instance status\n")
    sshprocess.stdin.close()

    for line in sshprocess.stdout:
        print(line)
    # Call check instance status to verify BAE API
    check_instance_status()


def check_instance_status():
    logger.info("Check BAE status")
    while True:
        try:
            r = requests.head('http://{host}:8080/bae/isAlive'.format(host=cpi_host))
            logger.debug(r.status_code)
            time.sleep(5)
            if r.status_code == 200:
                logger.info("BAE IS ALIVE!")
                break
        except requests.ConnectionError:
            logger.info("failed to connect")


def main():
    print("Script will start now")
    ask_user_jtl()


if __name__ == "__main__":
    main()

