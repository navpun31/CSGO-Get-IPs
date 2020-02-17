# =======================
# Author : Naveen Punjabi
# =======================

import os, re, ctypes, sys, wmi, time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys


Servers = [
	# "13.127.146.155",
	"45.117.203.250",
	"13.234.138.91",
	"13.233.187.225",
	"172.105.43.26",
	"13.235.72.160",
	"122.160.167.48",
	"45.117.204.250",
	"13.232.245.238",
	# "13.234.99.54",
	"172.105.50.114",
	"13.235.108.33",
	# "13.235.35.244",
]

Required_Ping = 60
Logging = True # Print the logs

Credentials = ("username", "password")
Cred_File = "credentials.txt"

IP_Base = "172.16"
IP_Series = [80]
Gateway_Series = 80
SubnetMask = "255.255.252.0"
Min_IP = 2
Max_IP = 10
Stride = 8

Logout_File = "logouts.txt"
IP_File = "ip.txt"


def log(text):
	if Logging:
		print(text)


class Driver:
	def __init__(self):
		self.driver = webdriver.Firefox()

	def login(self):
		logout_url = None
		try:
			self.driver = webdriver.Firefox()
			log(self.driver)

			# Redirecting to Network Authentication Page
			link = "http://detectportal.firefox.com/"
			self.driver.get(link)

			login_url = self.driver.current_url
			logout_url = login_url.replace('fgtauth', 'logout')
			log(login_url)

			username = self.driver.find_element_by_id("ft_un")
			password = self.driver.find_element_by_id("ft_pd")

			username.send_keys(Credentials[0])
			password.send_keys(Credentials[1])

			# Getting "Continue" Button
			button = self.driver.find_element_by_xpath("//form//div//input[@type='submit']")
			button.click()

			return logout_url

		except:
			return logout_url


	def logout(self, logout_url = None):
		try:
			log(logout_url)
			self.driver.get(logout_url)	
		except:
			return False
		return True


	def quit(self):
		self.driver.close()


def change_ip(my_ip, subnet, gateway):	
	try:
		# Obtain network adaptors configurations
		nic_configs = wmi.WMI().Win32_NetworkAdapterConfiguration(IPEnabled=True)

		# First network adaptor
		nic = nic_configs[0]

		# Set IP address, subnetmask and default gateway
		nic.EnableStatic(IPAddress=[my_ip],SubnetMask=[subnet])
		nic.SetGateways(DefaultIPGateway=[gateway])
		
		log("\n\n\nIP changed to " + my_ip)
		return True

	except:
		log("\n\n\nError changing IP to " + my_ip)
		return False	


def get_ping(server_ip):
	log("Pinging " + server_ip)
	try:
		# Pinging server
		ping_str = os.popen('ping -n 1 ' + server_ip + ' | find "ms"').read().split("\n")[1]
	except:
		# Couldn't connect
		log("Couldn't ping " + server_ip)
		return None

	ping_list = [ int(s[:-2]) for s in re.findall(r'\b\d+ms', ping_str) ]
	# Returning average of Min / Max / Avg ping values
	return sum(ping_list) / (len(ping_list) + 0.001)


def get_pings():
	return list( filter(None, [get_ping(ip) for ip in Servers]) )


def write_logout_url(logout_url):
	with open(Logout_File, "a") as file:
		file.write(logout_url + "\n")


def write_ip(text):
	with open(IP_File, "a") as file:
		file.write(text + "\n")


def get_ips(ip_base = "172.16", ip_series = [80, 81, 82], gateway_series = 80, subnet = "255.255.252.0"):
	# Result IPs
	ips = []
	browser = Driver()
	logout_urls = []

	gateway = ip_base + '.' + str(gateway_series) + '.1'
	for series in ip_series:
		for ending in range(Min_IP, Max_IP, Stride):
			my_ip = ip_base + '.' + str(series) + '.' + str(ending)

			# Changing IP
			if not change_ip(my_ip, subnet, gateway):
				continue
			
			# Login
			logout_url = browser.login()
			if logout_url:
				write_logout_url(logout_url)
				logout_urls.append(logout_url)
				log("Logged in successfully")
			else:
				log("Error logging in")
				browser.logout()
				browser.quit()
				continue

			# Pinging the Servers
			pings = get_pings()
			log(my_ip + " : " + str(pings))

			average = sum(pings) / len(pings)
			log("Avg: " + str(average))

			if average <= Required_Ping:
				ips += [(average, my_ip)]
				write_ip(str(int(average)) + " | " + str(my_ip))
				log(my_ip)

			# Network Logout
			new_logout_urls = []
			for logout_url in logout_urls:
				if browser.logout(logout_url):
					log("Logged out successfully")
				else:
					log("Error logging out")
					new_logout_urls.append(logout_url)

			browser.quit()

			logout_urls.clear()
			logout_urls += new_logout_urls

	for logout_url in logout_urls:
		if browser.logout(logout_url):
			log("Logged out successfully")
		else:
			log("Error logging out")

	return ips


def pending_logouts():
	# Logouts
	with open(Logout_File, "r") as file:
		data = file.readlines()

	browser = Driver()
	for logout_url in data:
		browser.logout(logout_url)
	browser.quit()


def clear_file(file_name):
	open(file_name, "w").close()


def load_credentials(file_name):
	# try:
	global Credentials
	with open(file_name, "r") as file:
		Credentials = (file.readline().replace('\n',''), file.readline().replace('\n',''))
	log("Credentials loaded successfully")
	return True

	# except:
	# 	log("Failed to load credentials")
	# 	return False


def main():
	if load_credentials(Cred_File):
		# Clear the "results" file
		clear_file(IP_File)

		# Obtain best IPs
		result = get_ips(ip_base=IP_Base, ip_series=IP_Series, gateway_series=Gateway_Series, subnet=SubnetMask)
		print( sorted(result) )

		# Logout pending sessions
		pending_logouts()
		clear_file(Logout_File)


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


# Check for admin rights
if is_admin():
	main()	
else:
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)


