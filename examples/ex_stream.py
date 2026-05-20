import time

import numpy as np

from labjackt7 import LabjackT7
from labjackt7.channels import StreamChannels


def main():
    # stream_out_in_1kHz_pwm()

    # stream_in_example()

    periodic_stream_example()

    return


def stream_in_example():
    lj = LabjackT7()

    scan_rate = 500
    input_channels = ["AIN0"]

    #stream burst
    act_rate, data = lj.stream.stream_burst(input_channels, scanRate=scan_rate, scanTime_s=1)
    print(f"Len: {len(data)}, Mean: {np.mean(data)}, Min: {np.min(data)}, Max: {np.max(data)}")
    plot_stream([data])

    # standard stream:
    stream_samples = []
    lj.stream.stream_start(input_channels, scan_rate=scan_rate)
    for n in range(4):
        samples = lj.stream.stream_read()
        stream_samples.append(samples)
        time.sleep(1)
    print(f"Len: {len(stream_samples)}, Mean: {np.mean(stream_samples)}, Min: {np.min(stream_samples)}, Max: {np.max(stream_samples)}")
    plot_stream([stream_samples])

def stream_out_in_1kHz_pwm():
    lj = LabjackT7()

    scan_rate = 10000
    pwm_frequeny = 1000
    pwm_waveform = np.array([0] * int(scan_rate/pwm_frequeny/2) + [1] * 5, dtype=np.uint16)
    dio1_reads = []
    ain0_reads = []

    # create a waveform to output this on DIO0
    fio_state_waveform = lj.digital.array_to_bitmask(pwm_waveform.reshape(-1, 1), [0])

    # Stream the FIO bank so bit 1 can be decoded as the DIO1 input state.
    input_channels = ["FIO_STATE", "AIN0"]

    try:
        lj.stream.configure()
        lj.stream.set_inhibit([0])
        actual_scan_rate = lj.stream.stream_in_out(
            input_channels=input_channels,
            scan_rate=scan_rate,
            scans_per_read=scan_rate,
            stream_out=[{
                "target": 4040,
                "data": fio_state_waveform,
                "dtype": "U16",
                "loop": 1,
            }],
        )

        print(f"Streaming started at {actual_scan_rate} scans/s")
        print(f"  DIO0 will output a PWM signal")
        print(f"  Connect this to FIO0 and DIO1 to sample analog and digitally")

        for read_index in range(5):
            data, device_backlog, ljm_backlog = lj.stream.stream_read()
            scans = np.asarray(data, dtype=float).reshape(-1, len(input_channels) + 1)

            fio_state = scans[:, 0].astype(np.uint16)
            dio1 = ((fio_state & (1 << 1)) != 0).astype(np.uint8)
            ain0 = scans[:, 1]
            dio1_reads.append(dio1)
            ain0_reads.append(ain0)

            print(
                f"Read {read_index + 1}: samples={len(scans)} "
                f"DIO1[0:8]={dio1[:8].tolist()} "
                f"AIN0[0:8]={ain0[:8].tolist()} "
                f"device_backlog={device_backlog} "
                f"ljm_backlog={ljm_backlog}"
            )
            time.sleep(0.1)
    finally:
        lj.stop()

    plot_in_out_stream(dio1_reads, ain0_reads)

def plot_stream(data:list[list]):
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


def periodic_stream_example():
    '''
    Configure DAC 1 to output 100Hz sine wave and DAC1 to output 200Hz.

    We setup the scan rate to be 10kHz.
    The sinewave for DAC0 is loaded into "stream_out_index" (buffer) 0, and DAC1 is in buffer 1.
    Note that we don't even have to make the buffers the same number of points (DAC1 is half
    the points of DAC0) and the stream works fine.
    '''
    lj = LabjackT7()

    scan_rate = 10000
    lj.waveform.configure(scan_rate, scans_per_read=1)
    
    # Setup 100Hz
    sine_wave_frequency = 100
    samples_per_period = scan_rate // sine_wave_frequency
    sine_wave = (0.5*np.sin(2.0 * np.pi * np.arange(samples_per_period) / samples_per_period)+0.5).tolist()
    # Add this waveform to output on DAC0, fed from buffer 0
    lj.waveform.add(sine_wave, target=StreamChannels.DAC0, stream_out_index=0)

    # Setup 200Hz
    sine_wave_frequency = 200
    samples_per_period = scan_rate // sine_wave_frequency
    sine_wave = (0.5*np.sin(2.0 * np.pi * np.arange(samples_per_period) / samples_per_period)+0.5).tolist()
    # Add this waveform to output on DAC1, fed from buffer 1
    lj.waveform.add(sine_wave, target=StreamChannels.DAC1, stream_out_index=1)

    print("Starting stream out on DAC0, for 10s...")
    lj.waveform.start()
    time.sleep(10)
    lj.waveform.stop()
    print("Stopping output")

if __name__ == "__main__":
    main()
