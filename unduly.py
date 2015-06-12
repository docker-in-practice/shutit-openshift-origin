"""ShutIt module. See http://shutit.tk
"""

from shutit_module import ShutItModule


class unduly(ShutItModule):


	def build(self, shutit):
		# Some useful API calls for reference. See shutit's docs for more info and options:
		#
		# ISSUING BASH COMMANDS
		# shutit.send(send,expect=<default>) - Send a command, wait for expect (string or compiled regexp)
		#                                      to be seen before continuing. By default this is managed
		#                                      by ShutIt with shell prompts.
		# shutit.multisend(send,send_dict)   - Send a command, dict contains {expect1:response1,expect2:response2,...}
		# shutit.send_and_get_output(send)   - Returns the output of the sent command
		# shutit.send_and_match_output(send, matches) 
		#                                    - Returns True if any lines in output match any of 
		#                                      the regexp strings in the matches list
		# shutit.run_script(script)          - Run the passed-in string as a script
		# shutit.install(package)            - Install a package
		# shutit.remove(package)             - Remove a package
		# shutit.login(user='root', command='su -')
		#                                    - Log user in with given command, and set up prompt and expects.
		#                                      Use this if your env (or more specifically, prompt) changes at all,
		#                                      eg reboot, bash, ssh
		# shutit.logout(command='exit')      - Clean up from a login.
		# 
		# COMMAND HELPER FUNCTIONS
		# shutit.add_to_bashrc(line)         - Add a line to bashrc
		# shutit.get_url(fname, locations)   - Get a file via url from locations specified in a list
		# shutit.get_ip_address()            - Returns the ip address of the target
		#
		# LOGGING AND DEBUG
		# shutit.log(msg)                    - Send a message to the log
		# shutit.pause_point(msg='')         - Give control of the terminal to the user
		# shutit.step_through(msg='')        - Give control to the user and allow them to step through commands
		#
		# SENDING FILES/TEXT
		# shutit.send_file(path, contents)   - Send file to path on target with given contents as a string
		# shutit.send_host_file(path, hostfilepath)
		#                                    - Send file from host machine to path on the target
		# shutit.send_host_dir(path, hostfilepath)
		#                                    - Send directory and contents to path on the target
		# shutit.insert_text(text, fname, pattern)
		#                                    - Insert text into file fname after the first occurrence of 
		#                                      regexp pattern.
		# ENVIRONMENT QUERYING
		# shutit.host_file_exists(filename, directory=False)
		#                                    - Returns True if file exists on host
		# shutit.file_exists(filename, directory=False)
		#                                    - Returns True if file exists on target
		# shutit.user_exists(user)           - Returns True if the user exists on the target
		# shutit.package_installed(package)  - Returns True if the package exists on the target
		# shutit.set_password(password, user='')
		#                                    - Set password for a given user on target

		# Clean up brutally:
		shutit.send('''docker ps -a | grep openshift-origin | awk '{print $1}' | xargs --no-run-if-empty docker rm -f''')
		shutit.send('''docker ps -a | grep k8 | awk '{print $1}' | xargs --no-run-if-empty docker rm -f''')
		shutit.send('sh <(curl https://raw.githubusercontent.com/openshift/origin/master/examples/sample-app/pullimages.sh)')
		#shutit.send('docker run -d --name "openshift-origin" --net=host --privileged -v /var/run/docker.sock:/var/run/docker.sock -v /var/lib/openshift:/var/lib/openshift openshift/origin start')
		shutit.send('docker run -d --name "openshift-origin" --net=host --privileged -v /var/run/docker.sock:/var/run/docker.sock openshift/origin start')
		shutit.login(command='docker exec -it openshift-origin bash')
		shutit.send('cd /var/lib/openshift')
		shutit.send('mkdir -p examples/sample-app')
		shutit.send('wget https://raw.githubusercontent.com/openshift/origin/master/examples/sample-app/application-template-stibuild.json -O examples/sample-app/application-template-stibuild.json')
		#see here: https://github.com/openshift/origin/blob/master/examples/sample-app/README.md#application-build-deploy-and-update-flow, step 3')
		shutit.add_to_bashrc('export CURL_CA_BUNDLE=`pwd`/openshift.local.config/master/ca.crt #see here: https://github.com/openshift/origin/blob/master/examples/sample-app/README.md#application-build-deploy-and-update-flow, step 3')
		shutit.send('export CURL_CA_BUNDLE=`pwd`/openshift.local.config/master/ca.crt')
		shutit.send('sleep 30')
		shutit.send('''osadm registry --create --credentials=/var/lib/openshift/openshift.local.config/master/openshift-registry.kubeconfig --images='registry.access.redhat.com/openshift3_beta/ose-${component}:${version}' --selector="region=infra" --mount-host=/mnt/registry''')
		shutit.send('osc describe service docker-registry --config=openshift.local.config/master/admin.kubeconfig')
		shutit.send('osadm policy add-role-to-user view test-admin --config=openshift.local.config/master/admin.kubeconfig')
		shutit.multisend('osc login --certificate-authority=openshift.local.config/master/ca.crt',{'assword':'any','sername':'test-admin'})
		shutit.send('osc new-project test --display-name="OpenShift 3 Sample" --description="This is an example project to demonstrate OpenShift v3"')
		shutit.send('cd /var/lib/openshift/examples/sample-app')
		shutit.send('osc process -f application-template-stibuild.json | osc create -f -')
		shutit.send('sleep 30')
		shutit.send('osc build-logs ruby-sample-build-1')
		shutit.send('''echo navigate to: http://$(osc get service | awk '{print $4 $5}') ''')
		# auth
		shutit.send('osc project default')
		shutit.send('wget https://raw.githubusercontent.com/openshift/training/master/beta3/openldap-example.json')
		shutit.send('osc create -f openldap-example.json')
		shutit.send('sleep 30')
		shutit.install('openldap-clients')
		shutit.send('''ldapsearch -D 'cn=Manager,dc=example,dc=com' -b "dc=example,dc=com"            -s sub "(objectclass=*)" -w redhat            -h `osc get services | grep openldap-example-service | awk '{print $4}'`''')
		shutit.send('git clone https://github.com/openshift/training.git')
		#shutit.send('wget https://raw.githubusercontent.com/openshift/training/master/beta4/openldap-example.json')
		#shutit.send('osc create -f openldap-example.json')
		#shutit.send('sleep 30')
		#shutit.install('openldap-clients')
		#shutit.send('''ldapsearch -D 'cn=Manager,dc=example,dc=com' -b "dc=example,dc=com"            -s sub "(objectclass=*)" -w redhat            -h `osc get services | grep openldap-example-service | awk '{print $4}'`''')
		#shutit.send('cd training/beta4')
		#shutit.send('sh ./basicauthurl.sh')
		#shutit.send('osc create -f basicauthurl.json')
		#shutit.send('osc start-build basicauthurl-build')
		shutit.logout()
		return True

	def get_config(self, shutit):
		# CONFIGURATION
		# shutit.get_config(module_id,option,default=None,boolean=False)
		#                                    - Get configuration value, boolean indicates whether the item is 
		#                                      a boolean type, eg get the config with:
		# shutit.get_config(self.module_id, 'myconfig', default='a value')
		#                                      and reference in your code with:
		# shutit.cfg[self.module_id]['myconfig']
		return True

	def test(self, shutit):
		# For test cycle part of the ShutIt build.
		return True

	def finalize(self, shutit):
		# Any cleanup required at the end.
		return True
	
	def is_installed(self, shutit):
		return False


def module():
	return unduly(
		'shutit.unduly.unduly.unduly', 1788415931.00,
		description='',
		maintainer='',
		depends=['shutit.tk.setup']
	)

