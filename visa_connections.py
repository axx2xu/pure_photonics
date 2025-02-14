from pymeasure.adapters import VISAAdapter
import time
import pyvisa

################################################################################################################################################################################
#                               ****THIS IS A TEST CODE TO TEST THE CONNECTION TO THE ECL MODULE, IT FUNCTIONS IN WRITING TO AND ENABLING LASER 3 and 4****

################################################################################################################################################################################


# Initialize the VISA resource manager
rm = pyvisa.ResourceManager()

# List all connected VISA devices (Optional: To verify connections)
print("Connected devices:", rm.list_resources())