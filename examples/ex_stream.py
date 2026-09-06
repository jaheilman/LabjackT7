import time
import numpy as np
from labjackt7 import LabjackT7
from labjackt7.channels import StreamChannel


def main():

    ### STREAMING INPUTS ###

    ## Simple multi-channel input for a predetermined number of scans
    # ex_analog_streamburst_in()

    # ex_analog_stream_in()
    # ex_analog_stream_in_2ch()

    # ex_digital_stream_in()
    # ex_digitalport_stream_in()

    # ex_mixed_stream_in()


    ### STREAMING OUTPUTS ###

    ex_stream_dout()
    
    # ex_stream_aout()
    # ex_stream_aout_2ch()

    ## LJM PeriodicStreamOut is supported by labjackt7.waveform
    ## In theory this can mix analog and digital outputs.
    # ex_analog_out_waveform()


    ### STREAMING INPUTS AND OUTPUTS ###

    ## Digital loopback - in and out on one I/O
    # ex_digital_loopback()

    ## Stream output and input at the same time!
    # ex_analog_in_and_analog_out()



    return


def ex_analog_streamburst_in():
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

    '''
    Continuous streaming requires that the program periodically
    run a .read() to collect the buffer.

    Notice that you will setup "scans_per_read" which is
    the size of the buffer ljm will return in a read.
    If that buffer isn't ready, the read() call will block until
    it is.  If the buffer multiple groups of scans_per_read,
    each ready will only pop one, so you need to repeat calls
    to drain the swamp.

    '''

    lj = LabjackT7()

    # standard stream:
    scan_rate = 5000
    scans_per_second = 2
    scans_per_read = scan_rate // scans_per_second
    channels = ["AIN0"]
    # let's call read just a little before the buffer is ready.
    sleep_time_s = 0.9 // scans_per_read
    n_scans = 2

    stream_samples = []
    print(f"Streaming at {scan_rate} scans/s and collecting {n_scans} every {sleep_time_s} seconds...")
    start_time = time.perf_counter()
    actual_scan_rate = lj.stream.ain(channels, 
        scan_rate=scan_rate,
        scans_per_read = scans_per_read,
    )
    
    for n in range(n_scans):
        time.sleep(sleep_time_s)
        samples = lj.stream.read()
        stream_samples.extend(samples)
    stop_time = time.perf_counter()
    lj.stream.stop()
    print(f'Scanned for {stop_time - start_time}s')
    print(f"Len: {len(stream_samples)}, Mean: {np.mean(stream_samples)}, Min: {np.min(stream_samples)}, Max: {np.max(stream_samples)}")
    print(f"Actual scan rate: {actual_scan_rate}")
    _plot_stream([stream_samples])


def ex_analog_stream_in_2ch():
    print("Starting 2 CHANNEL ANALOG STREAM example...")

    lj = LabjackT7()

    # standard stream:
    scan_rate = 5000
    scans_per_read = scan_rate // 2
    channels = ["AIN0", "AIN1"]
    seconds_to_scan = 2

    stream_samples = []
    print(f"Streaming at {scan_rate} scans/s for {seconds_to_scan} seconds...")
    print(f"  Scanning channels {channels}")
    start_time = time.perf_counter()
    actual_scan_rate = lj.stream.ain(channels, 
        scan_rate=scan_rate,
        scans_per_read = scans_per_read,
    )
    
    while ((time.perf_counter() - start_time) < seconds_to_scan):
        samples = lj.stream.read()
        add_data(stream_samples, samples)
    stop_time = time.perf_counter()
    lj.stream.stop()
    print(f'Scanned for {stop_time - start_time}s')
    print(f"Len: {len(stream_samples)}, Mean: {np.mean(stream_samples)}, Min: {np.min(stream_samples)}, Max: {np.max(stream_samples)}")
    print(f"Actual scan rate: {actual_scan_rate}")


def ex_digital_stream_in():
    lj = LabjackT7()

    # standard stream:
    scan_rate = 5000
    scans_per_read = 1000
    seconds_to_scan = 0.3
    channels = ["FIO0", "FIO1"]

    stream_samples = [[],[]] # need to initialize shape
    print(f"Streaming at {scan_rate} scans/s for {seconds_to_scan} seconds...")
    print(f"  Scanning channels {channels}")
    start_time = time.perf_counter()
    actual_scan_rate = lj.stream.input(channels, 
        scan_rate=scan_rate,
        scans_per_read = scans_per_read,
    )
    
    while ((time.perf_counter() - start_time) < seconds_to_scan):
        samples = lj.stream.read()
        for chan_data, samples in zip(stream_samples,samples):
            chan_data.extend(samples)
    stop_time = time.perf_counter()
    lj.stream.stop()
    print(f'Scanned for {stop_time - start_time}s')
    print(f"Len: {len(stream_samples)}, Mean: {np.mean(stream_samples)}, Min: {np.min(stream_samples)}, Max: {np.max(stream_samples)}")
    print(f"Actual scan rate: {actual_scan_rate}")
    _plot_stream(stream_samples)


def ex_digitalport_stream_in():
    lj = LabjackT7()

    '''
    The entire digital port (FIO, MIO, CIO) can be sampled
    in one scan, with each bit representing the I/O port 
    '''

    # standard stream:
    scan_rate = 5000
    scans_per_read = 1000
    seconds_to_scan = 0.3
    channels = ["FIO_STATE"]

    #apply a signal to FIO0 and FIO1; set these two 
    lj.digital.dout('FIO2', 1)
    lj.digital.dout('FIO3', 0)

    stream_samples = []
    print(f"Streaming at {scan_rate} scans/s for {seconds_to_scan} seconds...")
    print(f"  Scanning channels {channels}")
    start_time = time.perf_counter()
    actual_scan_rate = lj.stream.input(channels, 
        scan_rate=scan_rate,
        scans_per_read = scans_per_read,
    )
    
    while ((time.perf_counter() - start_time) < seconds_to_scan):
        samples = lj.stream.read()
        stream_samples.extend(samples)
    stop_time = time.perf_counter()
    lj.stream.stop()
    print(f'Scanned for {stop_time - start_time}s')
    print(f"Len: {len(stream_samples)}, Mean: {np.mean(stream_samples)}, Min: {np.min(stream_samples)}, Max: {np.max(stream_samples)}")
    print(f"Actual scan rate: {actual_scan_rate}")

    # split off the lowest four bits, FIO0-3
    values = np.asarray(stream_samples, dtype=np.uint8).ravel()
    bit_channels = [((values >> bit) & 1).tolist() for bit in range(4)]
    _plot_stream(bit_channels)


def ex_stream_dout():
    print("Starting STREAM DIGITAL OUT example...")

    print(" THIS EXAMPLE IS NOT WORKING")
    return
    '''
    Digital only supports streaming to the whole port
    '''

    lj = LabjackT7()

    scan_rate = 2000
    period = 1/100
    duty = 0.4
    channels = 'FIO_STATE'

    samples_per_period = round(period * scan_rate)
    data = (np.arange(samples_per_period) < duty * samples_per_period).astype(np.uint8).tolist()

    actual_scan_rate = lj.stream.dout(
        channels, 
        data, 
        scan_rate=scan_rate)
    print(f"Streaming started at {actual_scan_rate} scans/s")
    print(f"  DIO0 will output a sinewave signal")


    print("Streaming for 3 seconds...")
    time.sleep(3)
    lj.stop()


def ex_digital_loopback():
    lj = LabjackT7()

    scan_rate = 2000
    scans_per_read = 1000
    seconds_to_scan = 0.4
    channels = ["FIO0"]

    stream_samples = []
    print(f"Streaming at {scan_rate} scans/s for {seconds_to_scan} seconds...")
    print(f"  Scanning channels {channels}")
    start_time = time.perf_counter()
    actual_scan_rate = lj.stream.input(channels, 
        scan_rate=scan_rate,
        scans_per_read = scans_per_read,
    )
    
    while ((time.perf_counter() - start_time) < seconds_to_scan):
        samples = lj.stream.read()
        for chan_data, samples in zip(stream_samples,samples):
            chan_data.extend(samples)
    stop_time = time.perf_counter()
    lj.stream.stop()
    print(f'Scanned for {stop_time - start_time}s')
    print(f"Len: {len(stream_samples)}, Mean: {np.mean(stream_samples)}, Min: {np.min(stream_samples)}, Max: {np.max(stream_samples)}")
    print(f"Actual scan rate: {actual_scan_rate}")
    _plot_stream(stream_samples)


def ex_mixed_stream_in():
    print("Starting MIXED ANALOG + DIGITAL STREAM example...")
    lj = LabjackT7()

    # standard stream:
    scan_rate = 5000
    scans_per_read = 2000
    seconds_to_scan = 0.1
    channels = ["AIN0", "FIO0"]

    lj.stream.configure(scan_rate=scan_rate)
    print(f"Streaming {channels} at {scan_rate} scans/s ...")
    stream_samples = []
    actual_scan_rate = lj.stream.input(
        channels, 
        scan_rate=scan_rate,
        scans_per_read = scans_per_read,
    )
    start_time = time.perf_counter()
    while ((time.perf_counter() - start_time) < seconds_to_scan):
        samples = lj.stream.read()
        add_data(stream_samples, samples)
    stop_time = time.perf_counter()
    lj.stream.stop()
    print(f'Scanned for {stop_time - start_time}s')
    print(f"Len: {len(stream_samples)}, Mean: {np.mean(stream_samples)}, Min: {np.min(stream_samples)}, Max: {np.max(stream_samples)}")
    print(f"Actual scan rate: {actual_scan_rate}")

    _plot_stream(stream_samples)

def ex_stream_aout():
    print("Starting STREAM ANALOG OUT example...")
    lj = LabjackT7()

    scan_rate = 50000
    sine_frequency = 1000
    cycles_in_buffer = 1
    samples = scan_rate // sine_frequency * cycles_in_buffer
    sinewave = 1.1 + np.sin(2 * np.pi * sine_frequency * np.arange(samples) / scan_rate)
    data = sinewave.tolist()

    # channels options - DAC0 or DAC1
    #channels = 0 # this means DAC0
    #channels = 'DAC0' 
    channels = StreamChannel.DAC0   # StreamChannel helps clarify what channels 
                                    # are supported in stream operations

    # you can pass them them as a list:
    #channels = [0] # or ['DAC0'] or [StreamChannel.DAC0]

    # and you can provide multiple channels at one:
    #channels = [StreamChannel.DAC0, StreamChannel.DAC1]
    #data = [sinewave, 0.5*sinewave] # DAC1 is half the amplitude of DAC0

    print('INFO:')
    print(f'  Scan rate: {scan_rate}')
    print(f'  Data buffer size: {len(data)}')

    try:
        actual_scan_rate = lj.stream.aout(channels, data, scan_rate=scan_rate)
        print(f"Streaming started at {actual_scan_rate} scans/s")
        print(f"  DIO0 will output a sinewave signal")
    except Exception as e:
        print(f"Error starting analog output stream: {e}")

    print("Streaming for 3 seconds...")
    time.sleep(3)
    lj.stop()


def ex_stream_aout_2ch():
    print("Starting STREAM OUT example...")
    lj = LabjackT7()

    scan_rate = 20000
    sine_frequency = 500
    cycles_in_buffer = 1
    samples = scan_rate // sine_frequency * cycles_in_buffer
    sinewave = 1.1 + np.sin(2 * np.pi * sine_frequency * np.arange(samples) / scan_rate)

    # data = [sinewave.tolist()]
    # channels = ['DAC0']

    data = [sinewave, sinewave]
    channels = [StreamChannel.DAC0, StreamChannel.DAC1]  


    actual_scan_rate = lj.stream.aout(channels, data, scan_rate=scan_rate)
    print(f"Streaming started at {actual_scan_rate} scans/s")
    print(f'Streaming on channels {channels}')


    print("Streaming for 3 seconds...")
    time.sleep(3)
    lj.stop()


def ex_analog_out_waveform():
    '''
    Configure DAC0 to output 100Hz sine wave and DAC1 to output 200Hz.

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


def ex_analog_in_and_analog_out():
    '''
    Stream 150Hz out on DAC0 and sample in on AIN0.

    add_outputs is useful for mixing simulatanous in and out.
    '''
    lj = LabjackT7()
    scan_rate = 10000
    lj.stream.configure(scan_rate=scan_rate, scans_per_read=scan_rate//2)

    # Setup 150Hz
    sine_wave_frequency = 50
    samples_per_period = scan_rate // sine_wave_frequency
    sinewave = 1.1 + np.sin(2.0 * np.pi * np.arange(samples_per_period) / samples_per_period)
    sinewave = sinewave.tolist()


    # Add this waveform to output on DAC0, fed from buffer 0
    lj.stream.add_output(
        StreamChannel.DAC0,     # channels
        sinewave,          # data 
        0,
    )

    lj.stream.add_input(
        "AIN0",  # channels 

    )

    '''
    Alright, pay attention.
    Configuring the output is pretty easy: once we start,
        the labjack will loop that output waveform indefinitely.
    The input needs to be read periodically read to keep the
        buffer from overflowing.
    
    Note that the scan_rate is 10000 (samples per second),
        and the scans_per_read is half that: 5000.
    We need to do a read at least twice per second.
        I'll go ahead and do it every 250ms to be safe.

    '''


    print("Starting stream out on DAC0 and in on AIN0 for 5s...")
    stream_samples = []
    lj.stream.start()
    print(f"Streaming at {scan_rate} scans/s and collecting four 4 seconds (in 4 reads)...")
    start_time = time.perf_counter()
    while (time.perf_counter() - start_time < 1):
        time.sleep(.25)
        samples = lj.stream.read()
        stream_samples.extend(samples)
    stop_time = time.perf_counter()
    lj.stream.stop()
    print("Stopping output")

    print(f'Sampled for {stop_time - start_time}s')
    print(f'Collected {len(stream_samples)} samples')
    _plot_stream([stream_samples])





def _plot_stream(data:list):
    if not data:
        return

    if not isinstance(data[0], list):
        data = [data]

    import matplotlib.pyplot as plt

    _, axes = plt.subplots(len(data), 1, squeeze=False)
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    for index, stream_data in enumerate(data):
        samples = np.arange(len(stream_data))
        axes[index, 0].plot(samples, stream_data, color=colors[index % len(colors)])
        axes[index, 0].set_title(f"Stream Data {index}")
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


    # helper function to extend collected samples
def add_data(data, new_data):
    if not data:
        data.extend([list(values) for values in new_data])
    else:
        for existing, values in zip(data, new_data):
            existing.extend(values)


if __name__ == "__main__":
    main()
