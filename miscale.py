#!/usr/bin/python
try:
    import time
    import sys
    import getopt
    import subprocess
    import datetime
    from struct import pack
    from struct import unpack
except:
    print( 'Import error, check requirements.txt' )
    sys.exit(1)

def help():
    print( 'Usage: miscale.py -m <MAC Address> [OPTION]' )
    print( 'Requires a MAC Address and at lease one option' )
    print( '' )
    print( 'Options' )
    print( '-l, --last-weight                       Fetches the last weight measurment performed by the scale.' )
    print( '-q, --weight-queue                      Checks the weight history queue of the scale.' )
    print( '    >> -N, --keep-weight-queue          Sub-option: Checks the weight history queue of the scale without clearing the queue.' )
    print( '-t, --check-datetime                    Checks scale DateTime against system Local DateTime.' )
    print( '-u, --update-datetime                   Checks scale DateTime against system Local DateTime and updates if needed.' )
    print( '    >> -F, --force-update-datetime      Sub-option: Updates scale DateTime against system Local DateTime.' )

def run_command( command,stop='Null',filter='Null' ):
        p = subprocess.Popen(command,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

        output=[]
        for line in iter(p.stdout.readline, b''):
            if( stop in line ):
                p.kill()
                break
            if( filter not in line ):
                output.append( line )
        return output

def format_timestamp( yearhex="99",monthhex="01",dayhex="01",hourhex="00",minutehex="00",secondhex="00" ):
    year = str( unpack( '<h', ( yearhex ).decode('hex'))[0] )
    month = str( unpack('<h', ( monthhex + '00' ).decode('hex'))[0] )
    day = str( unpack('<h', ( dayhex + '00' ).decode('hex'))[0] )
    hour = str( unpack('<h', ( hourhex + '00' ).decode('hex'))[0] )
    minute = str( unpack('<h', ( minutehex + '00' ).decode('hex'))[0] )
    second = str( unpack('<h', ( secondhex + '00' ).decode('hex'))[0] )

    try:
        timestamp = datetime.datetime.strptime(day+'/'+month+'/'+year+' '+hour+':'+minute+':'+second, '%d/%m/%Y %H:%M:%S')
    except:
        timestamp = datetime.datetime.strptime('01/01/1970 12:00:00', '%d/%m/%Y %H:%M:%S')

    return timestamp

def datetime_update( mac_address ):

    reset_datetime = "gatttool -b " + mac_address + " --char-write-req -a 0x001b -n 00000000000000000000"
    output = run_command( reset_datetime.split() )

    if( 'Characteristic value was written successfully' not in output[0] ):
        print( 'Error re-setting DateTime' )
        sys.exit(1)

    now = datetime.datetime.now()

    hex_year = pack('<h', now.year).encode('hex')
    current_datetime = (
                            hex_year[:2] + hex_year[2:]
                            + (pack('<h', now.month).encode('hex'))[:2]
                            + (pack('<h', now.day).encode('hex'))[:2]
                            + (pack('<h', now.hour).encode('hex'))[:2]
                            + (pack('<h', now.minute).encode('hex'))[:2]
                            + (pack('<h', now.second).encode('hex'))[:2]
                            + "03"
                            + "00"
                            + "00"
                        )

    set_datetime = "gatttool -b " + mac_address + " --char-write-req -a 0x001b -n " + current_datetime
    output = run_command( set_datetime.split() )

    if( 'Characteristic value was written successfully' not in output[0] ):
        print( 'Error updating DateTime' )
        sys.exit(1)

    return

def check_time( mac_address):
    read_time = 'gatttool -b ' + mac_address + ' --char-read -a 0x001b'
    output = run_command( read_time.split() )
    raw_time = output[0].split(':')[1].split()

    timestamp = format_timestamp( yearhex = raw_time[0]+raw_time[1] ,monthhex = raw_time[2],dayhex = raw_time[3],hourhex = raw_time[4],minutehex =  raw_time[5],secondhex =  raw_time[6] )

    return timestamp

def initialize( mac_address ):

    weight_history_enable = "gatttool -b " + mac_address + " --char-write-req -a 0x0022 -n 01968abd62"
    output = run_command( weight_history_enable.split() )
    if( 'Characteristic value was written successfully' not in output[0] ):
        print( 'Error enabling weight History' )
        sys.exit(1)

    set_notif = "gatttool -b " + mac_address + " --char-write-req -a 0x0023 -n 0100"
    output = run_command( set_notif.split() )
    if( 'Characteristic value was written successfully' not in output[0] ):
        print( 'Error enabling notifications' )
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

        weight = unpack("<h", (data[i][1]+data[i][2]).decode("hex"))[0]

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
    history = run_command( get_history.split(),'Notification handle = 0x0022 value: 03 \n','Characteristic value was written successfully\n' )

    stop_cmd = "gatttool -b " + mac_address + " --char-write-req -a 0x0022 -n 03"
    output = run_command( stop_cmd.split() )
    if( 'Characteristic value was written successfully' not in output[0] ):
        print( 'Error sending stop command' )

    data = history_clean( history )

    return data

def read_weight_queue( mac_address,keep_queue ):

    get_history_queue = "timeout 30s gatttool --listen -b " + mac_address + " --char-write-req -a 0x0022 -n 01FFFFFFFF"
    history_queue = run_command( get_history_queue.split() )
    reading_num = int(history_queue[1][39:-17], 16)

    if( reading_num > 0 ):
        print( str( reading_num ) + " Unread measurements" )

        get_weight_list = "gatttool --listen -b " + mac_address + " --char-write-req -a 0x0022 -n 02"
        history = run_command( get_weight_list.split(),'Notification handle = 0x0022 value: 03 \n','Characteristic value was written successfully\n' )

        stop_cmd = "gatttool -b " + mac_address + " --char-write-req -a 0x0022 -n 03"
        output = run_command( stop_cmd.split() )
        if( 'Characteristic value was written successfully' not in output[0] ):
            print( 'Error sending stop command' )

        if( not keep_queue ):
            acc_cmd = "gatttool -b " + mac_address + " --char-write-req -a 0x0022 -n 04FFFFFFFF"
            output = run_command( acc_cmd.split() )
            if( 'Characteristic value was written successfully' not in output[0] ):
                print( 'Error sending acknowledgment' )

        data = history_clean( history )

        return data

    return "No records"

def main(argv):
    mac_address = ''
    last_weight = False
    weight_queue = False
    keep_weight_queue = False
    check_datetime = False
    update_datetime = False
    force_update_datetime = False

    date_format = '%d/%m/%Y %H:%M:%S'
    try:
        opts, args = getopt.getopt(argv,'hm:lqNtuF',[ 'help',
                                                            'mac-address=',
                                                            'last-weight',
                                                            'weight-queue',
                                                            'keep-weight-queue',
                                                            'check-datetime',
                                                            'update-datetime',
                                                            'force-update-datetime'
                                                        ])
    except getopt.GetoptError:
        help()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            help()
            sys.exit(0)
        elif opt in ('-m', '--mac-address'):
            mac_address = arg
        elif opt in ('-l', '--last-weight'):
            last_weight = True
        elif opt in ('-q', '--weight-queue'):
            weight_queue = True
        elif opt in ('-N', '--keep-weight-queue'):
            keep_weight_queue = True
        elif opt in ('-t', '--check-datetime'):
            check_datetime = True
        elif opt in ('-u', '--update-datetime'):
            update_datetime = True
        elif opt in ('-F', '--force-update-datetime'):
            force_update_datetime = True

    if( check_datetime ):
        timestamp = check_time( mac_address )
        print( "Current DateTime: " + timestamp.strftime(date_format) )

    if( update_datetime ):

        timestamp = check_time( mac_address )

        now = datetime.datetime.now()

        if( force_update_datetime ):
            datetime_update( mac_address )

            time.sleep(5)

            new_timestamp = check_time( mac_address )
            print( "DateTime updated from: " + timestamp.strftime(date_format) + " to: " + new_timestamp.strftime(date_format))
        else:
                if( now.year != timestamp.year
                    or now.month != timestamp.month
                    or now.day != timestamp.day
                    or now.hour != timestamp.hour
                    or now.minute != timestamp.minute
                ):
                    print( "Updating DateTime" )
                    datetime_update( mac_address )

                    time.sleep(5)

                    new_timestamp = check_time( mac_address )
                    print( "DateTime updated from: " + timestamp.strftime(date_format) + " to: " + new_timestamp.strftime(date_format))

    if( last_weight ):
        initialize( mac_address )

        data = read_weight_history( mac_address )[-1]

        records = format_weight( [ data ] )

        for i in range( len( records ) ):
            print( records[i][0] + " " + records[i][1] + " " + records[i][2] )

    elif( weight_queue ):
        initialize( mac_address )

        data = read_weight_queue( mac_address,keep_weight_queue )

        records = format_weight( data )

        if records != "No records":
            for i in range( len( records ) ):
                print( records[i][0] + " " + records[i][1] + " " + records[i][2] )
        else:
            print records

if __name__ == "__main__":
    main(sys.argv[1:])
