#!/usr/bin/env python

# File name: mycloudsdk_external.py
# copyright: 2017 Western Digital Corporation. All rights reserved.

import requests
import json
import time

# MyCloud Account credentials
# Please update this before running the script
MYCLOUD_TEST_USER_NAME = '<username>'
MYCLOUD_TEST_PASSWORD = '<password>'
MYCLOUD_TEST_CLIENT_ID = '<client_id>'
MYCLOUD_TEST_CLIENT_SECRET = '<client_secret>'

# Base URL to get all mycloud server endpoints for each environment.
MYCLOUD_CONFIG_URL = 'https://config.mycloud.com/config/v1/config'

# Global variables for this demo app.
auth_url = ''
cloud_url = ''
auth_token = ''
user_id = ''
device_id = ''
device_url = ''


def init_mycloud_apis():
	''' This is the initialization method and will use mycloud base-url to get all mycloud service endpoint for the given environment.
	'''

	config_request = requests.get(MYCLOUD_CONFIG_URL)
	if (config_request.status_code == 200):
		parsed = json.loads(config_request.content)
		global auth_url
		global cloud_url
		try:
			auth_url = parsed["data"]["componentMap"]["cloud.service.urls"]["service.auth0.url"]
			cloud_url = parsed["data"]["componentMap"]["cloud.service.urls"]["service.device.url"]
			if (not auth_url or not cloud_url):
				print 'Auth url or Cloud url not found. Something went wrong in config service response'
				quit()	# quitting as program cannot proceed without server endpoints
			else:
				print 'My Cloud server end points'
				print 'Auth URL: ' + auth_url
				print 'Cloud URL: ' + cloud_url
		except:
			print 'Exception. Something went wrong in config service response'
			quit()	# quitting as program cannot proceed without server endpoints

	else:
		print 'Config server is not available'
		quit()	# quitting as program cannot proceed without server endpoints


def sign_in():
	''' This method will sign-in user to mycloud system and retrieve auth token.
		Please note that typically app developer has to follow standard OAuth2.0 redirect flow to get the access token.
		MyCloud tokens are valid for one hour. App can use refresh token to create new access token.
	'''

	payload = {
		'grant_type': 'http://auth0.com/oauth/grant-type/password-realm',
		'username': MYCLOUD_TEST_USER_NAME,
		'password': MYCLOUD_TEST_PASSWORD,
		'client_id': MYCLOUD_TEST_CLIENT_ID,
		'client_secret': MYCLOUD_TEST_CLIENT_SECRET,
		'scope': 'openid nas_read_only nas_read_write user_read offline_access',
		'realm': 'Username-Password-Authentication',
		'audience': 'mycloud.com'
	}

	headers = {
		'Content-Type': 'application/json'
	}

	signin_request = requests.post(auth_url + '/oauth/token', headers=headers, data=json.dumps(payload))
	if (signin_request.status_code == 200):
		parsed = json.loads(signin_request.content)
		global auth_token
		auth_token = parsed["access_token"]
		if not auth_token:
			print 'Access token not found. Something went wrong in getting mycloud token'
			quit()	# quitting as program cannot proceed without auth token
	else:
		print 'Something went wrong in getting mycloud token'
		print auth_url
		quit()	# quitting as program cannot proceed without auth token



def get_user_info():
	''' This method will get user information from mycloud system using access token.
	'''

	headers = {
		'authorization': 'Bearer ' + auth_token
	}

	user_request = requests.get(auth_url + '/userinfo', headers=headers)

	if (user_request.status_code == 200):
		try:
			parsed = json.loads(user_request.content)
			global user_id
			user_id = parsed["sub"]
			if not user_id:
				print 'User id not found. Something went wrong in getting user info'
				quit()	# quitting as program cannot proceed without user info
			print 'User ID: ' + user_id
		except:
			print 'Exception. Something went wrong in getting user info'
			quit()	# quitting as program cannot proceed without user info
	else:
		print 'Something went wrong in getting user info'
		quit()	# quitting as program cannot proceed without user info


def get_device_details():
	''' This method will get the MyCloud Device that is attached to the given user.
		MyCloud device will be sitting at user's home and client application needs to retrieve
		the routing informaton from mycloud server.
	'''

	headers = {
		'authorization': 'Bearer ' + auth_token
	}

	device_request = requests.get(cloud_url + '/device/v1/user/' + user_id, headers=headers)

	if (device_request.status_code == 200):
		try:
			parsed = json.loads(device_request.content)
			device_name = parsed["data"][0]["name"]
			print 'Device Name: ' + device_name

			global device_id
			device_id = parsed["data"][0]["deviceId"]
			if not device_id:
				print 'Device Id not found. Something went wrong in getting device info'
				quit()	# quitting as program cannot proceed without device id
			print 'Device ID: ' + device_id

			global device_url
			device_url = parsed["data"][0]["network"]["proxyURL"]
			if not device_url:
				print 'Device url not found. Something went wrong in getting device info'
				quit()	# quitting as program cannot proceed without device info
			print 'Device URL: ' + device_url
		except:
			print 'Exception. Something went wrong in getting device info'
			quit()	# quitting as program cannot proceed without device info
	else:
		print 'Something went wrong in getting device info'
		quit()	# quitting as program cannot proceed without device info



def get_folders(id):
	''' This method will get all files and folders in a given folder-id.
	'''

	headers = {
		'authorization': 'Bearer ' + auth_token
	}
	file_search_url = device_url + '/sdk/v2/filesSearch/parents?ids='+ id +'&limit=100'	# paginate at 100 items per page
	device_request = requests.get(file_search_url, headers=headers)
	if (device_request.status_code == 200):
		print 'Files in ' + id
		parsed = json.loads(device_request.content)
		files = parsed["files"]
		for file in files:
			print file["name"]
	else:
		print 'Something went wrong in getting items from a folder'


def create_folder(folder_name):
	''' This method will create a folder in root level.
		App can crate folders wherever they want using folder id.
		My Cloud file/folder creation uses multipart/related
	'''

	headers = {
		'authorization': 'Bearer ' + auth_token,
		'Content-Type': 'multipart/related;boundary=mycloudboundary'
	}
	payload = {
		'name': folder_name,
		'parentID': 'root',
		'mimeType':'application/x.wd.dir'
	}
	# format payload data in multipart/related style
	post_data = '\r\n--mycloudboundary\r\n\r\n' + json.dumps(payload) + '\r\n--mycloudboundary--'

	folder_create_url = device_url + '/sdk/v2/files'
	create_folder_request = requests.post(folder_create_url, headers=headers, data=post_data)
	#print create_folder_request.status_code
	if (create_folder_request.status_code == 201) :
		print 'Folder created'
		try:
			# Newly created folder's id will be available in response header. for example, location:/sdk/v2/files/FHIRL1GEpZeK1y
			location_value = create_folder_request.headers['location']
			new_folder_id = location_value.split('files/')[1]
			return new_folder_id
		except:
			print 'Something went wrong in getting newly created folder id'
	elif (create_folder_request.status_code == 409) :
		print 'Folder already exists'
	else:
		print 'Folder creation failed'


def create_file(file_name, folder_id, file_content):
	''' This method will create a new file in given folder.
		My Cloud file/folder creation uses multipart/related
	'''
	headers = {
		'authorization': 'Bearer ' + auth_token,
		'Content-Type': 'multipart/related;boundary=mycloudboundary'
	}
	payload_header_data = {
		'name': file_name,
		'parentID': folder_id,
		'mimeType': 'text/plain'
	}

	# format payload data in multipart/related style
	post_data = '\r\n--mycloudboundary\r\n\r\n' + json.dumps(payload_header_data) + '\r\n--mycloudboundary\r\n\r\n' + file_content +'\r\n--mycloudboundary--'

	#print post_data
	folder_create_url = device_url + '/sdk/v2/files'

	create_folder_request = requests.post(folder_create_url, headers=headers, data=post_data)
	#print create_folder_request.status_code
	if (create_folder_request.status_code == 201) :
		print 'File created in folder'
		try:
			# Newly created file's id will be available in response header. for example, location:/sdk/v2/files/FHIRL1GEpZeK1y
			location_value = create_folder_request.headers['location']
			return location_value.split('files/')[1]
		except:
			print 'Exception. Something went wrong in getting newly created file id'
	elif (create_folder_request.status_code == 409) :
		print 'File already exists'
	else:
		print 'File creation failed'

def read_file_metadata(file_id):
	''' This method will read the metadata of a given file/folder.
	'''
	headers = {
		'authorization': 'Bearer ' + auth_token
	}
	metadata_request = requests.get(device_url + '/sdk/v2/files/' + file_id, headers=headers)
	#print metadata_request.status_code
	if (metadata_request.status_code == 200):
		print 'File Metadata'
		json_pretty_print(metadata_request.content)
	else:
		print 'Something went wrong in getting file metadata'


def read_file_content(file_id):
	''' This method will read the content of a given file.
	'''
	headers = {
		'authorization': 'Bearer ' + auth_token
	}
	content_request = requests.get(device_url + '/sdk/v2/files/' + file_id + '/content', headers=headers)
	#print content_request.status_code
	if (content_request.status_code == 200):
		print 'Dumping file content. ' + content_request.content
	else:
		print 'Something went wrong in getting file content'


def delete_file(file_id):
	''' This method will delete a given file.
	'''
	headers = {
		'authorization': 'Bearer ' + auth_token
	}
	content_request = requests.delete(device_url + '/sdk/v2/files/' + file_id, headers=headers)
	#print content_request.status_code
	if (content_request.status_code == 204):
		print 'File successfully deleted'
	else:
		print 'Something went wrong in deleting file'


def json_pretty_print(json_string):
	''' This is a utility function for JSON pretty print '''

	parsed = json.loads(json_string)
	print json.dumps(parsed, indent=4, sort_keys=True)


def run_demo_scripts():
	''' This method will execute few MyCloud ReST SDK Apis.
	'''

	# Initial steps
	sign_in() # MyCloud token is valid for one hour, app can save auth token to skip signin call.
	get_user_info()
	get_device_details()

	# Folder and file creation steps
	get_folders('root') # Root folder of the mycloud system is always 'root'
	timestamp = int(round(time.time() * 1000))
	folder_id = create_folder(str(timestamp)) # App can save newly created folder for future use. Creating new folder each time may create too many folders at root level
	file_id = create_file(str(timestamp) + '.txt', folder_id, 'This is a mycloud demo file.') # creating a sample text as file content.

	# File read stesps
	read_file_metadata(file_id)
	read_file_content(file_id)

	# File delete step
	delete_file(file_id)


print '======================================='
print 'Welcome to My Cloud SDK Quick Demo App'
print '======================================='
print ""
print '==============================================================================='
print 'Please update this script with your My Cloud Account details before proceeding.'
print '==============================================================================='

init_mycloud_apis()
run_demo_scripts()
print 'My Cloud SDK Demo Completed'
