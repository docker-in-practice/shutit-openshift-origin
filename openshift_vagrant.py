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
		mem_needed = int(shutit.cfg[self.module_id]['mem_needed'])
		whoami = shutit.whoami()
		for c in ('git',):
			if not shutit.command_available(c):
				shutit.install(c)
		shutit.send('cd')
		if not shutit.file_exists('origin',directory=True):
			shutit.send('git clone https://github.com/openshift/origin -b ' + shutit.cfg[self.module_id]['version'])
			shutit.send('cd origin')
			shutit.insert_text('      v.gui = true','Vagrantfile','config.vm.provider "virtualbox"')
			shutit.replace_text('''    "memory"            => ENV['OPENSHIFT_MEMORY'] || 2048,''','Vagrantfile',"""    "memory"            => ENV.'OPENSHIFT_MEMORY'""")
			memavail = shutit.get_memory()
			if memavail < mem_needed * 1000:
				if not shutit.get_input('Memory available appears to be: ' + str(memavail) + 'kB, need ' + str(mem_needed * 1000) + 'kB available to run.\nIf you want to continue, input "y", else "n"',boolean=True):
					shutit.fail('insufficient memory')
			name = 'origin_openshiftdev_'
			shutit.send('vagrant up')
			self._build_openshift(shutit)
		else:
			shutit.send('cd origin')
			shutit.send('git pull origin v1.0.1')
			if shutit.send_and_match_output('vagrant status',['.*running.*','.*saved.*','.*poweroff.*','.*not created.*','.*aborted.*']):
				if not shutit.send_and_match_output('vagrant status',['.*running.*']) and shutit.get_input('A vagrant setup already exists here. Do you want me to start up the existing instance (y) or destroy it (n)?',boolean=True):
					shutit.send('vagrant up')
					self._build_openshift(shutit)
				elif not shutit.send_and_match_output('vagrant status',['.*running.*']):
					shutit.send('vagrant destroy -f')
					shutit.send('cd ..')
					shutit.send('rm -rf origin')
					self.build(shutit)
					return True
			else:
				shutit.fail('should not get here')
		self._take_snapshot(shutit)
		return True

	def _build_openshift(self,shutit):
		shutit.login(command='vagrant ssh')
		shutit.login(command='sudo su')
		shutit.send('cd /data/src/github.com/openshift/origin/')
		shutit.send('./hack/build-release.sh')
		shutit.send('service openshift start')
		shutit.send('export KUBECONFIG=/openshift.local.config/master/admin.kubeconfig',note='Set the kubeconfig to the admin user')
		shutit.send('export REGISTRYCONFIG=/openshift.local.config/master/openshift-registry.kubeconfig',note='Use the registry kubeconfig')
		shutit.send_until('oadm registry --config=$KUBECONFIG --credentials=$REGISTRYCONFIG','invalid',note='Set up registry',not_there=True)
		shutit.send('oadm router main-router --replicas=1 --credentials="$KUBECONFIG"',note='Set up router')
		shutit.send('cd examples/data-population')
		shutit.send('./populate.sh')
		shutit.send('yum -y groups install "KDE Plasma Workspaces"')
		shutit.send('nohup startx &')
		#shutit.log('Now:\n1) Go to https://localhost:8443\n2) Set up a project with the mysql\n3) Connect to the mysql service with the mysql -hIP -uUSERNAME -pPASSWORD  ',add_final_message=True)
		shutit.log('',add_final_message=True)
		shutit.logout()
		shutit.logout()
		pwd = shutit.send_and_get_output('pwd')
		shutit.log('To work on this image from the last point\n    cd ' + pwd + '\n    vagrant snapshot back\nand wait a while before using\n\nIf you want to save state:\n    cd ' + pwd + '\n    vagrant snapshot take <name>',add_final_message=True)

	def _take_snapshot(self,shutit):
		if not shutit.send_and_match_output('vagrant plugin list','vagrant-vbox-snapshot'):
			cmd = 'sudo vagrant plugin install vagrant-vbox-snapshot'
			pw = shutit.get_env_pass(shutit.whoami(),'Input your sudo password for the command: ' + cmd)
			shutit.multisend(cmd,{'assword':pw})
		snapshot_name = shutit.cfg['build']['build_id']
		shutit.send('vagrant snapshot take openshift_' + snapshot_name)
		shutit.log('Vagrant snapshot taken: ' + snapshot_name, add_final_message=True)
		


	def get_config(self, shutit):
		# CONFIGURATION
		# shutit.get_config(module_id,option,default=None,boolean=False)
		#                                    - Get configuration value, boolean indicates whether the item is 
		#                                      a boolean type, eg get the config with:
		# shutit.get_config(self.module_id, 'myconfig', default='a value')
		#                                      and reference in your code with:
		# shutit.cfg[self.module_id]['myconfig']
		shutit.get_config(self.module_id, 'mem_needed', '2048', hint='Amount of memory for machine in MB')
		shutit.get_config(self.module_id, 'version', 'v1.0.1', hint='Version of origin')
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

