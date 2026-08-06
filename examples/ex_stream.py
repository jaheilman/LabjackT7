import time
import numpy as np
from labjackt7 import LabjackT7
from labjackt7.channels import StreamChannel


def main():
    # ex_analog_stream_burst_in()

    ex_analog_stream_in()

    ex_analog_stream_in_add_inputs()

    # ex_stream_out()

    # ex_analog_out_waveform()

    # ex_analog_out_stream_aout()

    # ex_analog_out_stream_add_outputs()

    # ex_analog_in_and_out()



    return


def ex_analog_stream_burst_in():
    print("Starting ANALOG STREAM BURST example...")
    lj = LabjackT7()

    scan_rate = 5000
    channels = ["AIN0"]

    #stream burst
    act_rate, data = lj.stream.stream_burst(channels, scanRate=scan_rate, scanTime_s=1)
    print(f"Stream burst at {act_rate} scans/s")
    print(f"Len: {len(data)}, Mean: {np.mean(data)}, Min: {np.min(data)}, Max: {np.max(data)}")
    _plot_stream(data)


def ex_analog_stream_in():
    print("Starting ANALOG STREAM example...")
    lj = LabjackT7()

    # standard stream:
    scan_rate = 5000
    channels = ["AIN0"]
    stream_samples = []
    lj.stream.ain(channels, scan_rate=scan_rate)

    print(f"Streaming at {scan_rate} scans/s and collecting four 4 seconds (in 4 reads)...")
    for n in range(4):
        samples = lj.stream.read()
        stream_samples.extend(samples)
        time.sleep(1)
    lj.stream.stop()
    print(f"Len: {len(stream_samples)}, Mean: {np.mean(stream_samples)}, Min: {np.min(stream_samples)}, Max: {np.max(stream_samples)}")
    _plot_stream([stream_samples])


def ex_analog_stream_in_add_inputs():
    print("Starting ANALOG STREAM example with add_inputs()...")
    lj = LabjackT7()

    # standard stream:
    scan_rate = 5000
    channels = ["AIN0"]
    stream_samples = []
    lj.stream.configure(scan_rate=scan_rate)
    lj.stream.add_inputs(channels)

    print(f"Streaming at {scan_rate} scans/s and collecting 4x 1s reads...")
    lj.stream.start()
    for n in range(4):
        samples = lj.stream.read()
        stream_samples.extend(samples)
        time.sleep(1)
    lj.stream.stop()
    print(f"Len: {len(stream_samples)}, Mean: {np.mean(stream_samples)}, Min: {np.min(stream_samples)}, Max: {np.max(stream_samples)}")
    _plot_stream([stream_samples])


def ex_stream_out():
    print("Starting STREAM OUT example...")
    lj = LabjackT7()

    scan_rate = 50000
    sine_frequency = 1000
    samples = scan_rate // sine_frequency * 1 # 1 cycles
    sine_waveform_arr = np.sin(2 * np.pi * sine_frequency * np.arange(samples) / scan_rate)
    sine_waveform_arr = 0.5 * sine_waveform_arr + 0.6 # scale to 0-1V
    sine_waveform = sine_waveform_arr.tolist()

    # channels options - DAC0 or DAC1
    #channels = 0 # this means DAC0
    #channels = 'DAC0' 
    channels = StreamChannel.DAC0  # StreamChannel helps clarify what channels 
                                    # are supported in stream operations

    # you can pass them them as a list:
    #channels = [0] # or ['DAC0'] or [StreamChannel.DAC0]

    # and you can provide multiple channels at one:
    #channels = [StreamChannel.DAC0, StreamChannel.DAC1]
    #data = [sine_waveform, 0.5*sine_waveform] # DAC1 is half the amplitude of DAC0

    try:
        actual_scan_rate = lj.stream.aout(channels, sine_waveform)
        print(f"Streaming started at {actual_scan_rate} scans/s")
        print(f"  DIO0 will output a sinewave signal")
    except Exception as e:
        print(f"Error starting analog output stream: {e}")

    print("Streaming for 10 seconds...")
    time.sleep(10)
    lj.stop()



def ex_analog_out_waveform():
    '''
    Configure DAC 1 to output 100Hz sine wave and DAC1 to output 200Hz.

    We setup the scan rate to be 10kHz.
    The sinewave for DAC0 is loaded into "stream_out_index" (buffer) 0, and DAC1 is in buffer 1.
    Note that we don't even have to make the buffers the same number of points (DAC1 is half
    the points of DAC0) and the stream works fine.
    '''
    lj = LabjackT7()

    scan_rate = 20000
    lj.waveform.configure(scan_rate, scans_per_read=1)
    
    # Setup 100Hz
    sine_wave_frequency = 100
    samples_per_period = scan_rate // sine_wave_frequency
    sine_wave = (0.5*np.sin(2.0 * np.pi * np.arange(samples_per_period) / samples_per_period)+0.5).tolist()
    # Add this waveform to output on DAC0, fed from buffer 0
    lj.waveform.add(sine_wave, target=StreamChannel.DAC0, stream_out_index=0)

    # Setup 200Hz
    sine_wave_frequency = 200
    samples_per_period = scan_rate // sine_wave_frequency
    sine_wave = (0.5*np.sin(2.0 * np.pi * np.arange(samples_per_period) / samples_per_period)+0.5).tolist()
    # Add this waveform to output on DAC1, fed from buffer 1
    lj.waveform.add(sine_wave, target=StreamChannel.DAC1, stream_out_index=1)

    print("Starting stream out on DAC0, for 10s...")
    lj.waveform.start()
    time.sleep(10)
    lj.waveform.stop()
    print("Stopping output")



def ex_analog_out_stream_aout():
    '''
    Similar to the _waveform() example, but using the stream() 
    method instead of waveform().
    '''
    lj = LabjackT7()

    scan_rate = 20000
    lj.waveform.configure(scan_rate, scans_per_read=1)
    
    # Setup 100Hz
    sine_wave_frequency = 100
    samples_per_period = scan_rate // sine_wave_frequency
    sine_wave_100 = (0.5*np.sin(2.0 * np.pi * np.arange(samples_per_period) / samples_per_period)+0.5).tolist()
    # Add this waveform to output on DAC0, fed from buffer 0

    # Setup 200Hz
    sine_wave_frequency = 200
    samples_per_period = scan_rate // sine_wave_frequency
    sine_wave_200 = (0.5*np.sin(2.0 * np.pi * np.arange(samples_per_period) / samples_per_period)+0.5).tolist()

    lj.stream.aout(
        [StreamChannel.DAC0, StreamChannel.DAC1],     # channels
        [sine_wave_100, sine_wave_200],                 # data 
        scan_rate=scan_rate                             # sample rate
    )


    print("Starting stream out on DAC0 and DAC1, for 10s...")
    lj.stream.start()
    time.sleep(10)
    lj.stream.stop()
    print("Stopping output")


def ex_analog_out_stream_add_outputs():
    '''
    Similar to the _waveform() example,
    but using the stream.add_output() and stream.start() 

    add_outputs is useful for mixing in and out.
    '''
    lj = LabjackT7()
    scan_rate = 20000
    lj.stream.configure(scan_rate=scan_rate)

    # Setup 150Hz
    sine_wave_frequency = 100
    samples_per_period = scan_rate // sine_wave_frequency
    sine_wave_100 = (0.5*np.sin(2.0 * np.pi * np.arange(samples_per_period) / samples_per_period)+0.5).tolist()
    # Add this waveform to output on DAC0, fed from buffer 0

    # Setup 250Hz
    sine_wave_frequency = 200
    samples_per_period = scan_rate // sine_wave_frequency
    sine_wave_200 = (0.5*np.sin(2.0 * np.pi * np.arange(samples_per_period) / samples_per_period)+0.5).tolist()

    lj.stream.add_outputs(
        [StreamChannel.DAC0, StreamChannel.DAC1],     # channels
        [sine_wave_100, sine_wave_200],                 # data 
        [0, 1]
    )


    print("Starting stream out on DAC0 and DAC1 (the hard way) for 10s...")
    lj.stream.start()
    time.sleep(10)
    lj.stream.stop()
    print("Stopping output")


def ex_analog_in_and_out():
    '''
    Stream 150Hz out on DAC0 and sample in on AIN0.
    but using the stream.add_output(), stream.add_input() 

    add_outputs is useful for mixing in and out.
    '''
    lj = LabjackT7()
    scan_rate = 20000
    lj.stream.configure(scan_rate=scan_rate)

    # Setup 150Hz
    sine_wave_frequency = 150
    samples_per_period = scan_rate // sine_wave_frequency
    sine_wave_100 = (0.5*np.sin(2.0 * np.pi * np.arange(samples_per_period) / samples_per_period)+0.5).tolist()
    # Add this waveform to output on DAC0, fed from buffer 0


    lj.stream.add_output(
        StreamChannel.DAC0,     # channels
        sine_wave_100,          # data 
        0,
    )

    lj.stream.add_input(
        "AIN0",  # channels                      # stream_in_index
    )


    print("Starting stream out on DAC0 and in on AIN0 for 10s...")
    stream_samples = []
    lj.stream.start()
    print(f"Streaming at {scan_rate} scans/s and collecting four 4 seconds (in 4 reads)...")
    for n in range(2):
        samples = lj.stream.read()
        stream_samples.extend(samples)
        time.sleep(1)
    time.sleep(6)
    lj.stream.stop()
    print("Stopping output")

    _plot_stream([stream_samples])


def _plot_stream(data:list[list]):
    if not data:
        return

    import matplotlib.pyplot as plt

    _, ax = plt.subplots()
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    for index, stream_data in enumerate(data):
        samples = np.arange(len(stream_data))
        ax.plot(samples, stream_data, color=colors[index % len(colors)])
    # plt.xlabel("Sample")
    # plt.ylabel("Value")
    plt.title("Stream Data")
    plt.tight_layout()
    plt.show()

def plot_in_out_stream(dio1_reads, ain0_reads):
    if dio1_reads and ain0_reads:
        import matplotlib.pyplot as plt

        dio1 = np.concatenate(dio1_reads)
        ain0 = np.concatenate(ain0_reads)
        samples = np.arange(len(ain0))

        fig, ax1 = plt.subplots()
        ax1.step(samples, dio1, where="post", color="tab:orange")
        ax1.set_xlabel("Sample")
        ax1.set_ylabel("DIO1", color="tab:orange")
        ax1.tick_params(axis="y", labelcolor="tab:orange")
        ax1.set_ylim(-0.1, 1.1)

        ax2 = ax1.twinx()
        ax2.plot(samples, ain0, color="tab:blue")
        ax2.set_ylabel("AIN0", color="tab:blue")
        ax2.tick_params(axis="y", labelcolor="tab:blue")

        plt.title("DIO1 and AIN0 Stream Data")
        plt.tight_layout()
        plt.show()



if __name__ == "__main__":
    main()
