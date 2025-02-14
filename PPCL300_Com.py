#example on how to use ITLA_reference.py
import ITLA_reference as itla
import time

sercon = itla.ITLAConnect('com5', 9600) # To try multiple ports enter a list using ['com1','com2',...], or for a single port use 'com#'
if isinstance(sercon, int):
    print("Error connecting to serial port, error code:", sercon)
    exit(1)
print('Serial connection %s' % sercon)
# Proceed with communication...


result = itla.ITLA(sercon, 0x90, 2, 1)  # Write whisper mode
print("Set low-noise mode (whisper mode) result:", result)
time.sleep(2)  # Wait 500ms

print('Serial connection %s' %sercon)
print('NOP %d; Flags %d' %(itla.ITLA(sercon,0x00,0,0),itla.ITLA(sercon,0x00,0,0)>>8))
print('Serial %s' %(itla.ITLA(sercon,0x04,0,0)))
print('Power setpoint %d *0.01dBm' %(itla.ITLA(sercon,0x31,0,0)))
itla.ITLA(sercon,0x31,itla.ITLA(sercon,0x31,0,0)-75,1)
print('New power setpoint %d * 0.01dBm' %(itla.ITLA(sercon,0x31,0,0)))
print('Laser temcperature %d * 0.01C' %(itla.ITLASplitDual(itla.ITLA(sercon,0x58,0,0),0)))
print('Ambient temcperature %d * 0.01C' %(itla.ITLASplitDual(itla.ITLA(sercon,0x58,0,0),1)))
sercon.close()