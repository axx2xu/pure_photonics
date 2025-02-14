#save as ITLA_reference.py to use with sample code
import serial
import time
import struct
import threading

ITLA_NOERROR=0x00
ITLA_EXERROR=0x01
ITLA_AEERROR=0x02
ITLA_CPERROR=0x03
ITLA_NRERROR=0x04
ITLA_CSERROR=0x05

ITLA_ERROR_SERPORT=0x01
ITLA_ERROR_SERBAUD=0x02

READ=0
WRITE=1

latestregister=0
tempport=0
raybin=0
queue=[]
maxrowticket=0
AEA_reference=[]

_error=ITLA_NOERROR
seriallock=0

def byteconv(number):
    #Converts a number to a byte for serial communications
    if number>127: number=number-256
    if number>127 or number <-128: return(struct.pack('b',0))
    return(struct.pack('b',number))

def ITLALastError():
    #returns the error status from the last communication
    return(_error)

def SerialLock():
    #returns status of serial communications
    global seriallock
    return seriallock

def SerialLockSet():
    #locks serial communications until a response is received (for multi-thread applications)
    global seriallock
    seriallock=1

def SerialLockUnSet():
    #releases serial communications until a response is received (for multi-thread applications)
    global seriallock,queue
    seriallock=0
    queue.pop(0)

def checksum(byte0,byte1,byte2,byte3):
    #calculates checksum
    bip8=(byte0&0x0f)^byte1^byte2^byte3
    bip4=((bip8&0xf0)>>4)^(bip8&0x0f)
    return bip4

def Send_command(sercon,byte0,byte1,byte2,byte3):
    #sends command on serial interface
    global CoBrite
    sercon.write(byteconv(byte0))
    sercon.write(byteconv(byte1))
    sercon.write(byteconv(byte2))
    #double check that the module has not sent any response after 3 bytes. If it did we are out of sync and we need to fix
    if sercon.inWaiting()>0:
        sercon.flushInput()
        counter=0
        while sercon.inWaiting()<4 and counter<8:
            sercon.write(byteconv(0)) #send 0 command (NOP)
            time.sleep(0.02)
            counter=counter+1
        if counter<8:     #if counter is 8 we have not recovered
            sercon.flushInput()
            Send_command(sercon,byte0,byte1,byte2,byte3)
        return
    sercon.write(byteconv(byte3))

def Receive_response(sercon):
    #receive response on serial interface
    global _error,queue,CoBrite,CoBrite_AEA,commlog
    reftime=time.perf_counter()
    while sercon.inWaiting()<4:
        if time.perf_counter()>reftime+0.25: #timeout
            _error=ITLA_NRERROR
            return(0xFF,0xFF,0xFF,0xFF) #default response; indicates error
        time.sleep(0.001)
    try:
        byte0=ord(sercon.read(1))
        byte1=ord(sercon.read(1))
        byte2=ord(sercon.read(1))
        byte3=ord(sercon.read(1))
    except:
        byte0=0xFF
        byte1=0xFF
        byte2=0xFF
        byte3=0xFF
    if checksum(byte0,byte1,byte2,byte3)==byte0>>4: #verify checksum
        _error=byte0&0x03
        return(byte0,byte1,byte2,byte3)
    else:
        _error=ITLA_CSERROR
        return(byte0,byte1,byte2,byte3)

def ITLAConnect(ports, baudrate=9600):
    """
    Attempts to connect to the unit over one of the provided ports.
    ports: a list of port names (e.g., ['COM3', 'COM4', 'COM5'])
    baudrate: initial baud rate to try
    Returns the serial connection if successful, or an error code if not.
    """
    # If a single port is provided, wrap it in a list
    if not isinstance(ports, list):
        ports = [ports]

    for port in ports:
        try:
            # Try initial connection on the current port
            conn = serial.Serial('\\\\.\\' + str(port), baudrate, timeout=1)
        except serial.SerialException:
            continue  # Try the next port if this one fails

        # Try out different baud rates on this port
        baudrate2 = 4800
        while baudrate2 <= 115200:
            ITLA(conn, 0x00, 0, READ)  # Check if we get a response on NOP command
            if ITLALastError() != ITLA_NOERROR:
                # Go to the next baud rate
                if baudrate2 == 4800:
                    baudrate2 = 9600
                elif baudrate2 == 9600:
                    baudrate2 = 19200
                elif baudrate2 == 19200:
                    baudrate2 = 38400
                elif baudrate2 == 38400:
                    baudrate2 = 57600
                elif baudrate2 == 57600:
                    baudrate2 = 115200
                elif baudrate2 == 115200:
                    conn.close()
                    break  # Failed on this port, exit the inner loop
                # Reopen the port with the new baud rate
                conn.close()
                try:
                    conn = serial.Serial('\\\\.\\' + str(port), baudrate2, timeout=1)
                except serial.SerialException:
                    break
                teller3 = 0
                while teller3 < 5 and conn.inWaiting() < 4:
                    conn.write(chr(0).encode())
                    time.sleep(0.01)
                    teller3 += 1
                conn.read(conn.inWaiting())
            else:
                return conn  # Successful connection on this port and baud rate

    # If we reach here, none of the ports worked
    return ITLA_ERROR_SERPORT


def ITLA(sercon,register,data,rw):
    #main routine to communicate with the unit
    global latestregister,commlog,AEA_reference,queue,maxrowticket
    lock=threading.Lock()
    lock.acquire() #execution halted while other thread is being queue'ed (allows for timeout)
    rowticket=maxrowticket+1
    starttime=time.perf_counter()
    maxrowticket=rowticket
    queue.append(rowticket)
    lock.release() #queue updated, now release for next thread
    while queue[0]!=rowticket: #only start communication if previous communication has finished
        if time.perf_counter()-starttime>5: #timeout
            teller=0
            while teller<len(queue):
                if queue[teller]==rowticket: queue.pop(teller) #cleanup
                else: teller=teller+1
            return 65535
    if data<0: data=data+65536 #convert signed number to non-signed integer
    if rw==READ:
        byte2=int(data/256)
        byte3=int(data-byte2*256)
        latestregister=register
        Send_command(sercon,int(checksum(0,register,byte2,byte3))*16+READ,register,byte2,byte3)
        test=Receive_response(sercon)
        if (test[0]&0x03)==ITLA_AEERROR: #if AEA response
            AEA_reference.append(test[0])
            AEA_reference.append(test[1])
            AEA_reference.append(test[2])
            AEA_reference.append(test[3])
            response=AEA(sercon,test[2]*256+test[3])
        else: response= test[2]*256+test[3]
    else:
        byte2=int(data/256)
        byte3=int(data-byte2*256)
        Send_command(sercon,int(checksum(1,register,byte2,byte3))*16+WRITE,register,byte2,byte3)
        test=Receive_response(sercon)
        response= test[2]*256+test[3]
    lock.acquire()
    queue.pop(0)
    lock.release()
    return(response)

def AEA(sercon,bytes):
    #read AEA string
    global AEA_reference
    outp=''
    if (bytes>100): #mostly to capture errors, e.g. where the response is 65535
        print('Excessive AEA number encountered')
        return(outp)
    while bytes>0:
        Send_command(sercon,int(checksum(0,0x0B,0,0))*16,0x0B,0,0)
        test=Receive_response(sercon)
        outp=outp+chr(test[2])
        if bytes>1:outp=outp+chr(test[3]) #to catch case of odd number of bytes
        bytes=bytes-2
    return outp

def ITLASplitDual(input,rank):
    #For currenst and temps registers sequences of 16 bit integers are output as AEA; allows to extract the desired element
    teller=rank*2
    try:
        return(ord(input[teller])*256+ord(input[teller+1]))
    except:
        return(0)