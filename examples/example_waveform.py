import time
import numpy as np
from labjackt7 import LabjackT7
from labjackt7.channels import StreamChannel



def ex_analog_out_waveform():
    '''
    Configure DAC 1 to output 100Hz sine wave and DAC1 to output 200Hz.

    We setup the scan rate to be 10kHz.
    The sinewave for DAC0 is loaded into "stream_out_index" (buffer) 0, and DAC1 is in buffer 1.
    Note that we don't even have to make the buffers the same number of points (DAC1 is half
    the points of DAC0) and the stream works fine.
    '''
    lj = LabjackT7()

    scan_rate = 10000
    # You can configure rates separately, or provide them to start.
    #lj.waveform.configure(scan_rate, scans_per_read=1)
    
    # Setup 100Hz
    sine_wave_frequency = 100
    samples_per_period = scan_rate // sine_wave_frequency
    sine_wave = (0.5 + 0.5*np.sin(2.0 * np.pi * np.arange(samples_per_period) / samples_per_period)).tolist()
    # Add this waveform to output on DAC0, fed from buffer 0
    lj.waveform.add(
        sine_wave, 
        target=StreamChannel.DAC0, 
        scan_rate=scan_rate, 
        stream_out_index=0)

    # Setup 200Hz
    sine_wave_frequency = 200
    samples_per_period = scan_rate // sine_wave_frequency
    sine_wave =(0.5  + 0.5 * np.sin(2.0 * np.pi * np.arange(samples_per_period) / samples_per_period)).tolist()
    # Add this waveform to output on DAC1, fed from buffer 1
    lj.waveform.add(
        sine_wave, 
        target=StreamChannel.DAC1, 
        scan_rate=scan_rate,  
        stream_out_index=1)

    print("Starting stream out on DAC0, for 10s...")
    lj.waveform.start()
    time.sleep(5)
    lj.waveform.stop()
    print("Stopping output")

    # # # reset DAC0 output
    # lj.waveform.reset()

    # scan_rate = 5000
    # sine_wave_frequency = 50
    # samples_per_period = scan_rate // sine_wave_frequency
    # sine_wave = (0.5 + 0.5*np.sin(2.0 * np.pi * np.arange(samples_per_period) / samples_per_period)).tolist()
    # # Add this waveform to output on DAC0, fed from buffer 0
    # lj.waveform.add(
    #     sine_wave, 
    #     target=StreamChannel.DAC0, 
    #     scan_rate=scan_rate, 
    #     stream_out_index=0)

    # lj.waveform.add(
    #     sine_wave, 
    #     target=StreamChannel.DAC1, 
    #     scan_rate=scan_rate, 
    #     stream_out_index=1)

    print("Starting NEW stream with double scan rate...")
    lj.waveform.start()
    time.sleep(5)
    lj.waveform.stop()
    print("Stopping output")



if __name__ == "__main__":
    ex_analog_out_waveform()
