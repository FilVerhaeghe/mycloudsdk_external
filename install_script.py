import requests
import json
import os
import sys
import getopt
from itertools import count
import time
import getpass

from datetime import datetime

MYCLOUD_TEST_CLIENT_ID = 'wJOCrSgcA5MYImigQrueZv2ouJG7RVKD'
MYCLOUD_TEST_CLIENT_SECRET = '5wzYQxzvZ5AHT8Hmg2LL5Hq2asYyDlt1Db2zRSoWtaOhRVGBQRtEsyko7uIJdq_8'

class DeviceRestAPI(object):

    owner_access_token = ''
    _ids = count(0)

    def __init__(self, uut_ip=None, env=None, username=None, password=None):
        self.id = self._ids.next()
        self.uut_ip = uut_ip
        self.guid = None
        self.username = username
        self.password = password
        self.access_token = None
        self.access_token_time = None
        self.access_token_expired_time = 1800
        self.access_token_renew_time = 300

    def get_access_token(self):
        """
            Get access token of the user attached to device

            :return: Access token in String formet. ex. '3931eb3d-7ee2-4257-988f-3aeb7f6d520d'
        """
        if self.access_token_time:
   #         print('Access token existed, checking the expire time')
            current_time = datetime.now()
            time_passed = (current_time - self.access_token_time).seconds

            if time_passed < (self.access_token_expired_time - self.access_token_renew_time):
    #            print('Use old access token: {0}, it will be expired in {1} seconds'.\
     #               format(self.access_token, self.access_token_expired_time - time_passed))
                return self.access_token
        #    else:
         #       print('Renew the access token cause old one will be expired in {} seconds'.\
          #          format(self.access_token_expired_time - time_passed))
        else:
            print 'Access token not existed, get a new token'

        url = 'https://wdc.auth0.com/oauth/token'

        headers = {'Content-Type': 'application/json'}

        data = {'username': self.username,
                'password': self.password,
                'client_id': MYCLOUD_TEST_CLIENT_ID,
                'client_secret': MYCLOUD_TEST_CLIENT_SECRET,
                'scope': 'openid nas_read_only nas_read_write user_read device_read nas_app_management offline_access',
                'realm': 'Username-Password-Authentication',
                'audience': 'mycloud.com',
                'grant_type': 'http://auth0.com/oauth/grant-type/password-realm'}

        result = requests.post(url, data=json.dumps(data), headers=headers)

        if result.status_code == 200:
            self.access_token = result.json()['access_token']
            # If first user attached to device set owner access token
            if self.id == 0:
                DeviceRestAPI.owner_access_token = self.access_token
            self.access_token_time = datetime.now()
            print("Get access token successfully, token:{}".format(self.access_token))
            return self.access_token
        else:
            raise Exception('Failed to get access token, status code:{0}, error message:{1}'.
                            format(result.status_code, result.content))

    def get_user_id(self):
        """
            Get the user id by access token

            :return: A user id in String format. ex. '8a808b0456808ec30156dbcafdb963bb'
        """

        url = 'https://wdc.auth0.com/oauth/token'
        headers = {'Content-Type': 'application/json'}
        data = {'username': self.username,
                'password': self.password,
                'client_id': MYCLOUD_TEST_CLIENT_ID,
                'client_secret': MYCLOUD_TEST_CLIENT_SECRET,
                'scope': 'openid nas_read_only nas_read_write user_read device_read nas_app_management offline_access',
                'realm': 'Username-Password-Authentication',
                'audience': 'mycloud.com',
                'grant_type': 'http://auth0.com/oauth/grant-type/password-realm'}

        result = requests.post(url, data=json.dumps(data), headers=headers)

        if result.status_code == 200:
            token = result.json()['access_token']

        url = 'https://wdc.auth0.com/userinfo'
        headers = {'authorization': 'Bearer %s' % self.access_token}
        result = requests.get(url, headers=headers)
        if result.status_code == 200:
            user_id = result.json()['sub']
            print("Get user ID successfully, ID:{}".format(user_id))
            return user_id
        else:
            raise Exception('Failed to get user id, status code:{0}, error message:{1}'.format(result.status_code, result.content))


    def generate_upload_data_info(self, file_name, parent_folder):
        """
            Generate a data binary for uploading folder/file

            :param data_name: The name of folder/file that will be created in device
            :param file_content: The file content in binary format. If specified,
                                 a file will be creates, otherwise a folder will be created.
            :param parent_folder: The place where the folder/file will be created.
                                  Can be 'root' or a parent folder id, 'root' means the first layer of the user folder.
        """
        data = 'uploadFile'
        type = 'file'

    #    print('Generating upload {} info'.format(type))
        if parent_folder:
            folder_id_list = self.get_data_id_list()
            if parent_folder in folder_id_list.keys():
                parent_id = folder_id_list[parent_folder]
            else:
                raise Exception('Cannot find specified parent folder: {}'.format(parent_folder))
        else:
            parent_id = 'root'

        with open(os.path.join(os.getcwd(), data), 'w') as fo:
            fo.write('--foo\n\n')
            command = '{'
            command += '"parentID":"{0}", "name":"{1}"'.format(parent_id, "app.apk")
            command += '}\n'
            fo.write(command)
            fo.write('\n')
            fo.write('--foo \n')
            fo.write('\n')

            fo.write(open(os.path.abspath(file_name), 'rb').read())
            fo.write('\n')
            fo.write('--foo--\n')
            fo.close()


     #   print('Upload {} info generated successfully'.format(type))

    def upload_data(self, data_name, file_content=None, parent_folder=None):
        """
            Create folder or file in user root directory or in it's sub folders

            :param data_name: The name of created file or folder
            :param file_content: The data binary of a file. If specified, a file will be created,
                                 otherwise a folder will be created
            :param parent_folder: 'None' means folder/file will be created in root directory,
                                  otherwise it will be in specified sub-folder. Default is 'None'
        """
        data_type = 'file'
        data = 'uploadFile'

        self.generate_upload_data_info(data_name, parent_folder)
        access_token = self.get_access_token()
        url = 'http://{}/sdk/v2/files'.format(self.uut_ip)
        headers = {'Authorization': 'Bearer {}'.format(access_token),
                   'Content-Type': 'multipart/related;boundary=foo'}
        data = open(os.path.join(os.getcwd(), data), 'rb').read()
        result = requests.post(url=url, headers=headers, data=data)
        if result.status_code == 201:
            print('The {0}: {1} is successfully copied on the device'.format(data_type, data_name))
        elif result.status_code == 409:
            print('The {0} already exists on the device'.format(data_type))
        else:
            raise Exception('The {0} is not created successfully, status code: {1}, error message: {2}'.
                            format(data_type, result.status_code, result.content))

    def install_app(self, app_name, app_url):
        """
            Install app to device
        """
        access_token = self.get_access_token()

        url = 'http://{0}/sdk/v1/apps/{1}'.format(self.uut_ip, app_name)

        params = {'downloadURL': 'file://app.apk'}
        headers = {'Authorization':'Bearer {}'.format(access_token)}

        result = requests.put(url, headers=headers, params=params)
        if result.status_code == 204:
            print "Please wait, app is being installed"
        else:
            raise Exception('Failed to install app, status code:{0}, error message:{1}'.
                             format(result.status_code, result.content))

    def uninstall_app(self, app_name):
        """
            Install app to device
        """
        access_token = self.get_access_token()

        url = 'http://{0}/sdk/v1/apps/{1}'.format(self.uut_ip, app_name)

        headers = {'Authorization':'Bearer {}'.format(access_token)}
        result = requests.delete(url, headers=headers)

        if result.status_code == 204:
           # print('App uninstalled successfully, status code: {0}'.format(result.status_code))
           return 1
        elif result.status_code == 404:
           # print('App not installed')
           return 2
        else:
            raise Exception('Failed to uninstall app, status code:{0}, error message:{1}'.
                             format(result.status_code, result.content))


    def search_file_by_parent_and_name(self, name, parent_id='root'):
        """
            API "Search File By Parent And Name", the document link:
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#search-a-file-by-parent-and-name

            Searches for a file having the specified parentID and name.


        :param parent_id: The parent ID to search within.
                          A not present value will retrieve the root node the matches the name.
                          The value of root retrieves the file in the user's root that matches the name.
        :param name: The name of the file to search for.
        :return: File information in json format and how many time use for searching. Example:
                 {
                     "mimeType": "application/octet-stream",
                     "name": "wd_monarch.uboot32.fb.dvrboot.exe.bin",
                     "extension": ".bin",
                     "storageType": "local",
                     "mTime": "2016-11-14T13:15:14Z",
                     "eTag": "Ag",
                     "privatelyShared": False,
                     'parentID": "6fnLnjmERI3VdVLc9bMWfmeSWTN-KfpUxVx3z9aP",
                     "hidden": "none",
                     "publiclyShared": False,
                     "id": "0xejlal648iBjC2hrSPXGsrxRWC0x_lxtO_y3oJH",
                     "size": 841256
                 },
                 0:00:00.052704
        """
        # Todo: This method might be able to merge into "get_data_id_list" method?
       # print 'Searching file by parent_id:{0} and name: {1}'.format(parent_id, name)
        id_token = self.get_access_token()
        url = 'http://{}/sdk/v2/filesSearch/parentAndName'.format(self.uut_ip)
        headers = {'Authorization': 'Bearer {0}'.format(id_token)}
        params = {'parentID': parent_id,
                  'name': name}
        result = requests.get(url, headers=headers, params=params)
        if result.status_code == 200:
        #    print 'Search file by parent and name successfully!'
        #    print 'Search time: {}'.format(result.elapsed)
        #    print 'Search file by parent and name result:\n{}'.format(result.json())
            file_id = result.json()['id']
            return file_id
        else:
            raise Exception ('Search file by parent and name failed, status code:{0}, error log:{1}'.format(result.status_code, result.content))

    def delete_file(self, data_id):
        """
            API "Delete file", the document link:
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#delete-file

            Delete file by file ID

            :param data_id: The file/folder ID
            :return: Boolean, elapsed time
        """
        # print 'Deleting data with ID: {}'.format(data_id)
        id_token = self.get_access_token()
        url = 'http://{0}/sdk/v2/files/{1}'.format(self.uut_ip, data_id)
        headers = {'Authorization': 'Bearer {0}'.format(id_token)}
        result = requests.delete(url, headers=headers)
        if result.status_code == 204:
            # print 'Delete file copy successfully!'
            return True, result.elapsed
        else:
            raise Exception('Delete file failed, status code:{0}, error log:{1}'.format(result.status_code, result.content))

    def get_ip(self):
        """
            grabs devices attached to account
        """
        print "getting IP"

        url = 'https://device.mycloud.com/device/v1/user/{0}'.format(self.get_user_id())
        headers = {
        		'authorization': 'Bearer ' + self.access_token
        }
        result = requests.get(url, headers=headers)

        resultList = []
        data = result.json()['data']
        for i in data:
            resultList.append((i['name'], i['network']['internalURI']))

        return resultList

def prompt(argv):
    rest = DeviceRestAPI()

    # enters credentials
    user = raw_input("Please enter your MyCloud account emailId: ")
    password = getpass.getpass()
    env = "prod"

    rest = DeviceRestAPI(None, env, user, password)
    try:
        rest.get_access_token()
        print "Successfully authenticated"
        #rest.get_user_id()
    except Exception:
        print "Wrong credentials, please check your email/password"
        exit(0)

    # gets devices attached to account
    resultList = rest.get_ip()
    # remove WD Cloud from resultList
    resultList = [x for x in resultList if x[0]!='WD Cloud']

    # get results
    if len(resultList) == 0:
        print "invalid account, no IP found"
        exit(0)
    elif len(resultList) == 1:
        print "using ", resultList[0][0], "@IP: ",resultList[0][1]
        ip = resultList[0][1][7:]
        rest.uut_ip = ip
    else:
        print "please select the number corresponding to the device you'd like to use"
        for i in range(len(resultList)):
            print str(i+1) + ":", resultList[i][0], "@IP: ", resultList[i][1]

        number = int(raw_input(""))

        print "you picked", resultList[number-1][0], "@IP: ", resultList[number-1][1]

        if number > len(resultList) or number < 1:
            print "you have entered an invalid number"
            exit(0)

        # strip the http://
        ip = resultList[number-1][1][7:]
        rest.uut_ip = ip


    # enter 1 for install, 2 for uninstall
    number = int(raw_input("Please enter 1 for install, 2 for uninstall: "))
    if number != 1 and number != 2:
        print "You have entered an invalid number"
        exit(0)

    # enter path
    pkgName = raw_input("Please enter your application's package name: ")
    try:
        successCode = rest.uninstall_app(pkgName)
        # Only want to notify users of delete operation when they specify delete
        if number == 2:
            if successCode == 1:
                print "App uninstalled successfully"
            elif successCode == 2:
                print "App was never installed"
    except:
        print "uninstall failed, please try again"
        exit(0)

    if number == 1:
        try:
            # upload and install
            apkPath = raw_input("Please enter apk path: ")
            apkname = os.path.basename(apkPath)
            appURL = 'file://{}'.format(apkname)
            rest.upload_data(data_name=apkPath)
            rest.install_app(pkgName, appURL)
            time.sleep(10)
            # deletes the uploaded file
            file_id = rest.search_file_by_parent_and_name('app.apk')
            rest.delete_file(file_id)
            print 'You can now launch the app with the following URL: \n http://{0}/sdk/v1/apps/{1}/proxy/?redirect-ip=http://{0}/sdk/v1/apps/{1}/proxy/&access_token={2}'.format(ip, pkgName, rest.access_token)
        except:
            print "Install failed, please try again"
            exit(0)


if __name__ == "__main__":
    print "========================================================="
    print "My Cloud Home Device App Installation/Uninstallation Tool"
    print "========================================================="
    print ""
    print "========================================================================"
    print "Please make sure you are on the same network as your MyCloud home device"
    print "========================================================================"
    prompt(sys.argv[1:])
