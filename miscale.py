import sys
if sys.version_info[0] < 3:
	raise Exception( "Python 3 is required to run" )

from version import __version__ as version
from version import state

try:
	import time
	import sys
	import platform
	import argparse
	import logging
	import yaml
	import os
	import subprocess
	import datetime
	import codecs
	from struct import pack
	from struct import unpack
except:
	print( 'Import error, check requirements.txt' )
	sys.exit(1)

def run_command( command,stop=b'Null',filter=b'Null' ):
		p = subprocess.Popen(command,
									stdout=subprocess.PIPE,
									stderr=subprocess.PIPE)

		output=[]
		for line in iter(p.stdout.readline, b''):
			sys.stdout.flush()
			if( stop in line ):
				p.kill()
				break
			if( filter not in line ):
				output.append( line )
		return output

def format_timestamp( yearhex="99",monthhex="01",dayhex="01",hourhex="00",minutehex="00",secondhex="00" ):
	year = str( unpack( '<h', codecs.decode( yearhex, 'hex'))[0] )
	month = str( unpack('<h', codecs.decode( monthhex + b'00', 'hex'))[0] )
	day = str( unpack('<h', codecs.decode( dayhex + b'00', 'hex'))[0] )
	hour = str( unpack('<h', codecs.decode( hourhex + b'00', 'hex'))[0] )
	minute = str( unpack('<h', codecs.decode( minutehex + b'00', 'hex'))[0] )
	second = str( unpack('<h', codecs.decode( secondhex + b'00', 'hex'))[0] )

	try:
		timestamp = datetime.datetime.strptime(day+'/'+month+'/'+year+' '+hour+':'+minute+':'+second, '%d/%m/%Y %H:%M:%S')
	except:
		timestamp = datetime.datetime.strptime('01/01/1970 12:00:00', '%d/%m/%Y %H:%M:%S')

	return timestamp

def datetime_update( mac_address ):

	reset_datetime = "gatttool -b " + mac_address + " --char-write-req -a 0x001b -n 00000000000000000000"
	output = run_command( reset_datetime.split() )

	if( b'Characteristic value was written successfully' not in output[0] ):
		logger.warning( 'Error re-setting DateTime' )
		sys.exit(1)

	now = datetime.datetime.now()

	hex_year = codecs.encode( pack('<h', now.year), 'hex' )
	current_datetime = (
							hex_year[:2] + hex_year[2:]
							+ codecs.encode( pack('<h', now.month), 'hex' )[:2]
							+ codecs.encode( pack('<h', now.day), 'hex' )[:2]
							+ codecs.encode( pack('<h', now.hour), 'hex' )[:2]
							+ codecs.encode( pack('<h', now.minute), 'hex' )[:2]
							+ codecs.encode( pack('<h', now.second), 'hex' )[:2]
							+ b'03'
							+ b'00'
							+ b'00'
						)

	set_datetime = "gatttool -b " + mac_address + " --char-write-req -a 0x001b -n " + str( current_datetime )
	output = run_command( set_datetime.split() )

	if( b'Characteristic value was written successfully' not in output[0] ):
		logger.warning( 'Error updating DateTime' )
		sys.exit(1)

	return

def check_time( mac_address):
	read_time = 'gatttool -b ' + mac_address + ' --char-read -a 0x001b'
	output = run_command( read_time.split() )
	raw_time = output[0].split(b':')[1].split()

	timestamp = format_timestamp( yearhex = raw_time[0]+raw_time[1] ,monthhex = raw_time[2],dayhex = raw_time[3],hourhex = raw_time[4],minutehex =  raw_time[5],secondhex =  raw_time[6] )

	return timestamp

def initialize( mac_address ):

	weight_history_enable = "gatttool -b " + mac_address + " --char-write-req -a 0x0022 -n 01968abd62"
	output = run_command( weight_history_enable.split() )
	if( b'Characteristic value was written successfully' not in output[0] ):
		logger.warning( 'Error enabling weight History' )
		sys.exit(1)

	set_notif = "gatttool -b " + mac_address + " --char-write-req -a 0x0023 -n 0100"
	output = run_command( set_notif.split() )
	if( b'Characteristic value was written successfully' not in output[0] ):
		logger.warning( 'Error enabling notifications' )
		sys.exit(1)

	return

def format_weight( data, date_format = '%d/%m/%Y %H:%M:%S' ):

	weight_records = []

	for i in range(len(data)):
		byte0 = '{:b}'.format(int("0x62", 16)).zfill(8)

		if int( byte0[:1] ) == 1:
				unit = 'lbs'
		elif int( byte0[3:4] ) == 1:
				unit = 'jin'
		elif int( byte0[:1] ) == 0 and int( byte0[3:4] ) == 0:
				unit = 'kg'

		weight = unpack("<h", codecs.decode(data[i][1]+data[i][2],"hex"))[0]

		if unit == 'kg':
				weight = float(weight)/200

		timestamp = format_timestamp(yearhex=data[i][3]+data[i][4],monthhex=data[i][5],dayhex=data[i][6],hourhex=data[i][7],minutehex=data[i][8],secondhex=data[i][9])

		weight_records.append([timestamp.strftime(date_format), ( str ( weight ) ), unit])

	return weight_records

def history_clean( history ):

	data = []

	for i in range( len( history ) ):
		dual = history[i][36:95]
		data.append( dual[:29].split() )
		data.append( dual[30:].split() )

	data = [x for x in data if x]

	return data

def read_weight_history( mac_address ):

	get_history = "gatttool --listen -b " + mac_address + " --char-write-req -a 0x0022 -n 02"
	history = run_command( get_history.split(),b'Notification handle = 0x0022 value: 03 \n',b'Characteristic value was written successfully\n' )

	stop_cmd = "gatttool -b " + mac_address + " --char-write-req -a 0x0022 -n 03"
	output = run_command( stop_cmd.split() )
	if( b'Characteristic value was written successfully' not in output[0] ):
		logger.warning( 'Error sending stop command' )

	data = history_clean( history )

	return data

def read_weight_queue( mac_address,keep_queue ):

	get_history_queue = "timeout 30s gatttool --listen -b " + mac_address + " --char-write-req -a 0x0022 -n 01FFFFFFFF"
	history_queue = run_command( get_history_queue.split() )
	reading_num = int(history_queue[1][39:-17], 16)

	if( reading_num > 0 ):
		logger.info( str( reading_num ) + " Unread measurements" )

		get_weight_list = "gatttool --listen -b " + mac_address + " --char-write-req -a 0x0022 -n 02"
		history = run_command( get_weight_list.split(),b'Notification handle = 0x0022 value: 03 \n',b'Characteristic value was written successfully\n' )

		stop_cmd = "gatttool -b " + mac_address + " --char-write-req -a 0x0022 -n 03"
		output = run_command( stop_cmd.split() )
		if( b'Characteristic value was written successfully' not in output[0] ):
			logger.warning( 'Error sending stop command' )

		if( not keep_queue ):
			acc_cmd = "gatttool -b " + mac_address + " --char-write-req -a 0x0022 -n 04FFFFFFFF"
			output = run_command( acc_cmd.split() )
			if( b'Characteristic value was written successfully' not in output[0] ):
				logger.warning( 'Error sending acknowledgment' )

		data = history_clean( history )

		return data

	return "No records"

# Modified from https://stackoverflow.com/a/27974027
def sanitize( data ):
	if not isinstance( data, ( dict, list ) ):
		return data
	if isinstance( data, list ):
		return [ v for v in ( sanitize(v) for v in data ) if v ]
	return { k: v for k, v in ( (k, sanitize( v ) ) for k, v in data.items() ) if v is not None }

# From https://stackoverflow.com/a/7205672
def mergedicts(dict1, dict2):
	for k in set(dict1.keys()).union(dict2.keys()):
		if k in dict1 and k in dict2:
			if isinstance(dict1[k], dict) and isinstance(dict2[k], dict):
				yield (k, dict(mergedicts(dict1[k], dict2[k])))
			else:
				# If one of the values is not a dict, you can't continue merging it.
				# Value from second dict overrides one in first and we move on.
				yield (k, dict2[k])
				# Alternatively, replace this with exception raiser to alert you of value conflicts
		elif k in dict1:
			yield (k, dict1[k])
		else:
			yield (k, dict2[k])

if __name__ == '__main__':
	# Fetch root directory
	root = os.path.dirname (os.path.realpath( __file__ ) )

	congifg_file = os.path.join( root, 'config.yml' )

	parser = argparse.ArgumentParser()
	parser.add_argument( '-v', '--version',
							dest='version',
							action='store_true',
							default=False,
							help='Print Version Number' )
	parser.add_argument( '-s', '--quiet',
							dest='quiet',
							action='store_true',
							default=False,
							help='Disable console output' )
	parser.add_argument( '-c', '--configuration',
							dest='config_file',
							default=congifg_file,
							help='Specify a different config file' )
	parser.add_argument( '-m', '--mac-address',
							dest='mac_address',
							help='Disable console output' )
	parser.add_argument( '-l', '--last-weight',
							dest='last_weight',
							action='store_true',
							default=False,
							help='Fetches the last weight measurment performed by the scale.' )
	parser.add_argument( '-q', '--weight-queue',
							dest='weight_queue',
							action='store_true',
							default=False,
							help='Checks the weight history queue of the scale.' )
	parser.add_argument( '-N', '--keep-weight-queue',
							dest='keep_weight_queue',
							action='store_true',
							default=False,
							help='Sub-option: Checks the weight history queue of the scale without clearing the queue.' )
	parser.add_argument( '-t', '--check-datetime',
							dest='check_datetime',
							action='store_true',
							default=False,
							help='Checks scale DateTime against system Local DateTime.' )
	parser.add_argument( '-u', '--update-datetime',
							dest='update_datetime',
							action='store_true',
							default=False,
							help='Checks scale DateTime against system Local DateTime and updates if needed.' )
	parser.add_argument( '-F', '--force-update-datetime',
							dest='force_update_datetime',
							action='store_true',
							default=False,
							help='Sub-option: Updates scale DateTime against system Local DateTime.' )

	args = parser.parse_args()

	if args.version:
		print( "Version: " + version + " - " + state )
		exit()

	# Set default configuration options
	cfg_default = { 'MiScale Settings' : {
						'Date Format' : '%d/%m/%Y %H:%M:%S'
						},
					'Logging Settings' : {
						'Level' : 'WARNING',
						'Log to Console' : True,
						'Log to File' : False,
						'Logfile' : 'miscale.log'
						} }

	# Load the configuration yaml file
	with open( args.config_file, 'r' ) as ymlfile:
		cfg_file = yaml.safe_load( ymlfile )

	cfg_user = sanitize( cfg_file )

	config = dict( mergedicts(cfg_default,cfg_user) )

	del cfg_default
	del cfg_user

	# Store overrides
	if args.mac_address:
		config['MiScale Settings']['Mac Address'] = args.mac_address

	try:
		config['MiScale Settings']['Mac Address']
	except:
		parser.print_help(sys.stderr)
		sys.exit(1)

	if not args.last_weight and not args.weight_queue and not args.check_datetime and not args.update_datetime:
		parser.print_help(sys.stderr)
		sys.exit(1)

	# Set up Logging
	logger = logging.getLogger( __name__ )

	log_file = os.path.join( root, config['Logging Settings']['Logfile'] )

	# Set Log Level
	level = logging.getLevelName( config['Logging Settings']['Level'] )
	logger.setLevel( level )

	# Create a logging format
	formatter = logging.Formatter( '%(asctime)s %(levelname)s: %(message)s' )

	# Add the handlers to the logger
	if config['Logging Settings']['Log to File']:
		logfile_handler = logging.FileHandler( log_file )
		logfile_handler.setFormatter( formatter )
		logger.addHandler( logfile_handler )

	if config['Logging Settings']['Log to Console'] and not args.quiet:
		console_handler = logging.StreamHandler()
		console_handler.setFormatter( formatter )
		logger.addHandler( console_handler )

	# Enable/Disable Logging
	logger.disabled = not config['Logging Settings']['Enabled']

	logger.info( 'Platform: ' + platform.system() )
	logger.info( "Version: " + version + " - " + state )
	if state != 'stable':
		logger.warning( "State is not stable: " + state )

	if( args.check_datetime ):
		timestamp = check_time( config['MiScale Settings']['Mac Address'] )
		logger.info( "Current DateTime: " + timestamp.strftime( config['MiScale Settings']['Date Format'] ) )

	if( args.update_datetime ):

		timestamp = check_time( config['MiScale Settings']['Mac Address'] )

		now = datetime.datetime.now()

		if( args.force_update_datetime ):
			datetime_update( config['MiScale Settings']['Mac Address'] )

			time.sleep(5)

			new_timestamp = check_time( config['MiScale Settings']['Mac Address'] )
			logger.info( "DateTime updated from: " + timestamp.strftime( config['MiScale Settings']['Date Format'] ) + " to: " + new_timestamp.strftime( config['MiScale Settings']['Date Format'] ))
		else:
				if( now.year != timestamp.year
					or now.month != timestamp.month
					or now.day != timestamp.day
					or now.hour != timestamp.hour
					or now.minute != timestamp.minute
				):
					logger.info( "Updating DateTime" )
					datetime_update( config['MiScale Settings']['Mac Address'] )

					time.sleep(5)

					new_timestamp = check_time( config['MiScale Settings']['Mac Address'] )
					logger.info( "DateTime updated from: " + timestamp.strftime( config['MiScale Settings']['Date Format'] ) + " to: " + new_timestamp.strftime( config['MiScale Settings']['Date Format'] ))

	if( args.last_weight ):
		initialize( config['MiScale Settings']['Mac Address'] )

		data = read_weight_history( config['MiScale Settings']['Mac Address'] )[-1]

		records = format_weight( [ data ] )

		for i in range( len( records ) ):
			logger.info( records[i][0] + " " + records[i][1] + " " + records[i][2] )

	elif( args.weight_queue ):
		initialize( config['MiScale Settings']['Mac Address'] )

		data = read_weight_queue( config['MiScale Settings']['Mac Address'],args.keep_weight_queue )

		records = format_weight( data )

		if records != "No records":
			for i in range( len( records ) ):
				logger.info( records[i][0] + " " + records[i][1] + " " + records[i][2] )
		else:
			logger.info( records )
