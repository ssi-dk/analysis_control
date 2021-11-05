import paramiko

username = input('Username: ')
password = input('Password: ')
passphrase = input('Passphrase: ')

mykey = paramiko.RSAKey.from_private_key_file(f'/home/{username}/.ssh/id_rsa', passphrase)

ssh_client = paramiko.client.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_client.connect('localhost', username=username, password=password, pkey=mykey)

stdin, stdout, stderr = ssh_client.exec_command('uptime')
print(stdout.readlines())
ssh_client.close()