from labjackt7 import LabjackT7

labjack = LabjackT7()

# Simple analog output and input
labjack.analog.aout('DAC0', 1)
voltage = labjack.analog.ain('AIN0')
print(f"voltage {voltage}")

# Set DAC0 to 2 V
labjack.analog.aout(0, 2)
voltage = labjack.analog.ain(0)
print(f"voltage {voltage}")

# Set DAC1 to 3 V
labjack.analog.aout('DAC1', 1)
voltage = labjack.analog.ain(0)
print(f"voltage {voltage}")

