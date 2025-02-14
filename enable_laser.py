import ITLA_reference as itla

# Connect to the laser on COM5 (or a list of ports)
sercon = itla.ITLAConnect('com5', 9600)
if isinstance(sercon, int):
    print("Error connecting to serial port, error code:", sercon)
    exit(1)
print('Serial connection %s' % sercon)

# Set the starting frequency by programming the "first channel frequency"
# For example, assume we want a base frequency corresponding to 193.43 THz.
# The registers are defined as:
#   - 0x35: First Channel Frequency (1 THz part)
#   - 0x36: First Channel Frequency (0.1 GHz part)
#   - 0x67: First Channel Frequency (1 MHz part)
# You will need to convert your desired frequency into the appropriate values.
# (This example uses placeholder values.)
first_channel_thz = 193  # Integer part (e.g., 193 THz)
first_channel_sub = 43   # Fractional part; conversion might be needed based on documentation
# Write to registers (the exact conversion and write sequence depends on your calibration)
itla.ITLA(sercon, 0x35, first_channel_thz, 1)  # WRITE operation for THz part
itla.ITLA(sercon, 0x67, first_channel_sub, 1)  # WRITE operation for sub-THz part
# You may also need to write to 0x67 if fine tuning at the MHz level is required

# Optionally, apply a fine frequency offset using register 0x62 (FTF)
# For example, to shift the frequency by +10 MHz:
itla.ITLA(sercon, 0x62, 10, 1)

# Verify by reading back the current frequency
current_freq_thz = itla.ITLA(sercon, 0x40, 0, 0)
current_freq_mhz = itla.ITLA(sercon, 0x68, 0, 0)
print("Current laser frequency (THz):", current_freq_thz)
print("Current laser frequency (MHz):", current_freq_mhz)
fractional = itla.ITLA(sercon, 0x41, 0, 0)
print("Fractional frequency (0.1 MHz units):", fractional)


sercon.close()
