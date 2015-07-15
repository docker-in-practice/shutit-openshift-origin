"""ShutIt module. See http://shutit.tk
"""

from shutit_module import ShutItModule


class openshift_vagrant(ShutItModule):


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
		# shutit.send_until(send,regexps)    - Send command over and over until one of the regexps seen in the output.
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
		# shutit.log(msg,add_final_message=False) -
		#                                      Send a message to the log. add_final_message adds message to
		#                                      output at end of build
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
		vagrant_dir = shutit.cfg[self.module_id]['vagrant_dir']
		memavail = shutit.get_memory()
		if memavail < 3500:
			if not shutit.get_input('Memory available appears to be: ' + str(memavail) + 'kB, need 3500kB available to run.\nIf you want to continue, input "y", else "n"',boolean=True):
				shutit.fail('insufficient memory')
		if shutit.send_and_get_output('''VBoxManage list runningvms | grep openshift-vagrant | grep -v 'not created' | awk '{print $1}' ''') != '':
			if shutit.get_input('Clean up your VMs first, as there appears to be a running openshift-vagrant VM in existence. Want me to clean them up for you?',boolean=True):
				shutit.multisend('vagrant destroy',{'y/N':'y'})
		whoami = shutit.whoami()
		for c in ('git',):
			if not shutit.command_available(c):
				shutit.install(c)
		shutit.send('cd')
		if not shutit.file_exists('origin',directory=True):
			shutit.send('git clone https://github.com/openshift/origin')
			shutit.send('cd origin')
			shutit.insert_text('      v.gui = true','Vagrantfile','config.vm.provider "virtualbox"')
			shutit.replace_text('''    "memory"            => ENV['OPENSHIFT_MEMORY'] || 2048,''','Vagrantfile',"""    "memory"            => ENV.'OPENSHIFT_MEMORY'""")
			shutit.send('vagrant up')
			self._build_openshift(shutit)
		else:
			shutit.send('cd origin')
			shutit.send('git pull')
			if shutit.send_and_match_output('vagrant status',['.*saved.*','.*poweroff.*','.*not created.*','.*aborted.*']):
				if shutit.get_input('Do you want me to start up the existing instance (y) or destroy it (n)?',boolean=True):
					shutit.send('vagrant up')
					self._build_openshift(shutit)
				else:
					shutit.send('vagrant destroy -f')
					shutit.send('cd ..')
					shutit.send('rm -rf origin')
					self.build(shutit)
					return True
			elif shutit.send_and_match_output('vagrant status','.*running.*'):
				if shutit.get_input('Do you want me to start up the existing instance (y), or destroy and start again (n)?',boolean=True):
					shutit.send('vagrant up')
					self._build_openshift(shutit)
				else:
					shutit.send('vagrant halt')
					shutit.send('vagrant destroy -f')
					shutit.send('cd ..')
					shutit.send('rm -rf origin')
					self.build(shutit)
					return True
			else:
				shutit.fail('should not get here')
		return True

	def _build_openshift(self,shutit):
		shutit.login(command='vagrant ssh')
		shutit.login(command='sudo su')
		shutit.send('cd /data/src/github.com/openshift/origin/')
		shutit.send('./hack/build-release.sh')
		shutit.send('service openshift start')
		shutit.send('ln -s /data/src/github.com/openshift/origin/_output/local/go/bin/openshift /bin/oc')
		shutit.send('ln -s /data/src/github.com/openshift/origin/_output/local/go/bin/openshift /bin/osadm')
		shutit.send('export KUBECONFIG=/openshift.local.config/master/admin.kubeconfig',note='Set the kubeconfig to the admin user')
		shutit.send('export REGISTRYCONFIG=/openshift.local.config/master/openshift-registry.kubeconfig','Use the registry kubeconfig')
		shutit.send('oadm registry --config=$KUBECONFIG --credentials=$REGISTRYCONFIG',note='Set up registry')
		shutit.send('oadm router main-router --replicas=1 --credentials="$KUBECONFIG"',note='Set up router')
		shutit.send('oc create -f examples/image-streams/image-streams-centos7.json -n openshift',note='centos7 image streams')
		shutit.send('oc create -f examples/db-templates -n openshift',note='db templates')
		# Enterprise version only
		#shutit.send('oc create -f examples/quickstart-templates -n openshift',note='core quickstart templates')
		#shutit.send('oc create -f examples/xpaas-streams/jboss-image-streams.json -n openshift',note='eap image streams')
		#shutit.send('oc create -f examples/xpaas-templates -n openshift','eap templates')
		shutit.send('yum -y groups install "KDE Plasma Workspaces"')
		shutit.send('nohup startx &')
		shutit.log('Now:\n1) Go to https://localhost:8443\n2) Set up a project with the mysql\n3) Connect to the mysql service with the mysql -hIP -uUSERNAME -pPASSWORD  ',add_final_message=False) -
		shutit.logout()
		shutit.logout()


	def get_config(self, shutit):
		# CONFIGURATION
		# shutit.get_config(module_id,option,default=None,boolean=False)
		#                                    - Get configuration value, boolean indicates whether the item is 
		#                                      a boolean type, eg get the config with:
		# shutit.get_config(self.module_id, 'myconfig', default='a value')
		#                                      and reference in your code with:
		# shutit.cfg[self.module_id]['myconfig']
		shutit.get_config(self.module_id, 'vagrant_dir', '/tmp/vagrant_dir')
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
	return openshift_vagrant(
		'shutit.openshift_vagrant.openshift_vagrant.openshift_vagrant', 1308628950.00,
		description='',
		maintainer='',
		delivery_methods = ('bash'),
		depends=['shutit.tk.setup','tk.shutit.vagrant.vagrant.vagrant','shutit-library.virtualbox.virtualbox.virtualbox']
	)

