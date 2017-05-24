#!/usr/bin/python
try:
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
    print( 'Requires a MAC Address at a minimum.' )
    print( '' )
    print( 'Options' )
    print( '-l, --last-weight           [Default] Fetches the last weight measurment performed by the scale.' )
    print( '-q, --weight-que            Checks the weight history que of the scale.' )
    print( '-N, --noclear-weight-que    Checks the weight history que of the scale without clearing the que.' )
    print( '-t, --check-time            Checks scale DateTime against system Local time.' )
    print( '-u, --update-time           Checks scale DateTime against system Local time and updates if needed.' )
    print( '-F, --force-update-time     Updates scale DateTime against system Local time.' )

def run_command( command ):
        p = subprocess.Popen(command,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

        output=[]
        for line in iter(p.stdout.readline, b''):
            output.append( line )
        return output

def format_timestamp( yearhex="00",monthhex="00",dayhex="00",hourhex="00",minutehex="00",secondhex="00" ):
    year = str( unpack( '<h', ( yearhex ).decode('hex'))[0] )
    month = str( unpack('<h', ( monthhex + '00' ).decode('hex'))[0] )
    day = str( unpack('<h', ( dayhex + '00' ).decode('hex'))[0] )
    hour = str( unpack('<h', ( hourhex + '00' ).decode('hex'))[0] )
    minute = str( unpack('<h', ( minutehex + '00' ).decode('hex'))[0] )
    second = str( unpack('<h', ( secondhex + '00' ).decode('hex'))[0] )

    timestamp = datetime.datetime.strptime(day+'/'+month+'/'+year+' '+hour+':'+minute+':'+second, '%d/%m/%Y %H:%M:%S')

    return timestamp

def update_datetime( mac_address ):

    reset_datetime = "gatttool -b " + mac_address + " --char-write -a 0x001b -n 00000000000000000000"
    output = run_command( reset_datetime.split() )

    if(output[0] != 'Characteristic value was written successfully\n'):
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

    set_datetime = "gatttool -b " + mac_address + " --char-write -a 0x001b -n " + current_datetime
    output = run_command( reset_datetime.split() )

    if(output[0] != 'Characteristic value was written successfully\n'):
        print( 'Error updating DateTime' )
        sys.exit(1)

    return

def check_time( mac_address):
    read_time = 'gatttool -b ' + mac_address + ' --char-read -a 0x001b'
    output = run_command( fetch_time.split() )
    raw_time = output[0].split(':')[1].split()

    timestamp = format_timestamp( yearhex = raw_time[0]+raw_time[1] ,monthhex = raw_time[2],dayhex = raw_time[3],hourhex = raw_time[4],minutehex =  raw_time[5],secondhex =  raw_time[6] )

    return timestamp

def initialize( mac_address ):

    weight_history_enable = "gatttool -b " + mac_address + " --char-write-req -a 0x0022 -n 01968abd62"
    output = run_command( weight_history_enable.split() )
    if(output[0] != 'Characteristic value was written successfully\n'):
        print( 'Error enabling weight History' )
        sys.exit(1)

    set_notif = "gatttool -b " + mac_address + " --char-write-req -a 0x0023 -n 0100"
    output = run_command( set_notif.split() )
    if(output[0] != 'Characteristic value was written successfully\n'):
        print( 'Error enabling notifications' )
        sys.exit(1)

    return

def format_weight( data ):

    for i in range(len(data)):
        byte0 = bin(int(data[i][0].decode("hex"), 16))[2:].zfill(8)

        if int( byte0[:1] ) == 1:
                unit = 'lbs'
        elif int( byte0[3:4] ) == 1:
                unit = 'jin'
        elif int( byte0[:1] ) == 0 and int( byte0[3:4] ) == 0:
                unit = 'kg'

        weight = unpack("<h", (data[i][1]+data[i][2]).decode("hex"))[0]

        if unit == 'kg':
                weight = float(weight)/200

        timestamp = read_timestamp(yearhex=data[i][3]+data[i][4],monthhex=data[i][5],dayhex=data[i][6],hourhex=data[i][7],minutehex=data[i][8],secondhex=data[i][9])

        weight_records.append([timestamp, ( str ( weight ) )])

    return weight_records

def weight_history( mac_address ):

    data = []

    initialize( mac_address )

    get_history = "timeout 30s gatttool --listen -b " + mac_address + " --char-write-req -a 0x0022 -n 02"
    history = run_command( get_history_que.split() )

    stop_cmd = "gatttool -b " + mac_address + " --char-write -a 0x0022 -n 03"
    output = run_command( stop_cmd.split() )
    if(output[0] != 'Characteristic value was written successfully\n'):
        print( 'Error sending stop command' )

    history = history[1].split(":")[1].split()

    i = 0
    while ( i < ( reading_num*10 ) ):
        data.append( raw_data[i:i+10] )
        i = i + 10

    return data

def weight_que( mac_address,clear_que=True ):

    data = []

    initialize( mac_address )

    get_history_que = "timeout 30s gatttool --listen -b " + mac_address + " --char-write-req -a 0x0022 -n 01FFFFFFFF"
    history_que = run_command( get_history_que.split() )
    reading_num = int(history_que[1][39:-17], 16)

    if( reading_num > 0 ):
        print( str( reading_num ) + " Unread measurments" )

        get_weight_list = "timeout 30s gatttool --listen -b " + mac_address + " --char-write-req -a 0x0022 -n 02"
        weight_list = run_command( get_weight_list.split() )

        stop_cmd = "gatttool -b " + mac_address + " --char-write -a 0x0022 -n 03"
        output = run_command( stop_cmd.split() )
        if(output[0] != 'Characteristic value was written successfully\n'):
            print( 'Error sending stop command' )

        if( clear_que ):
            acc_cmd = "gatttool -b " + mac_address + " --char-write -a 0x0022 -n 04FFFFFFFF"
            output = run_command( acc_cmd.split() )
            if(output[0] != 'Characteristic value was written successfully\n'):
                print( 'Error sending acknowledgment' )

        raw_data = weight_list[1].split(":")[1].split()

        i = 0
        while ( i < ( reading_num*10 ) ):
            data.append( raw_data[i:i+10] )
            i = i + 10

        return data


def main(argv):
    mac_address = ''
    date_format = '%m/%d/%y'
    try:
        opts, args = getopt.getopt(argv,'hm:',['mac_address='])
    except getopt.GetoptError:
        print 'test.py -m <MAC Address>'
        sys.exit(2)

    if( update_time ):

        timestamp = check_time( mac_address )

        now = datetime.datetime.now()

        if( force_update_time ):
            update_datetime( mac_address )
        else:
                if( now.year != timestamp.year
                    or now.month != timestamp.month
                    or now.day != timestamp.day
                    or now.hour != timestamp.hour
                    or now.minute != timestamp.minute
                ):
                    update_datetime( mac_address )

if __name__ == "__main__":
    main(sys.argv[1:])