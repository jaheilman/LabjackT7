import time
import numpy as np
from labjackt7 import LabjackT7


def main():
    pulse_example()

    # pwm_example()

    # pwm_loopback_example()

    return


def pulse_example():
    lj = LabjackT7()

    pulse_freq = 1000
    pulse_duty = .200
    # create a waveform to output this on DIO0
    lj.pwm.pulse(
        channel='DIO0', 
        frequency = pulse_freq,
        duty_cycle = pulse_duty,
        count = 1
    )


def pwm_example():
    lj = LabjackT7()

    freq = 2000
    duty = .4
    # create a waveform to output this on DIO0
    lj.pwm.start(
        channel='DIO0', 
        frequency = freq,
        duty_cycle = duty
    )

    time.sleep(10)

    lj.pwm.stop()



def pwm_loopback_example():
    lj = LabjackT7()

    freq = 100
    duty = .4
    # create a waveform to output this on DIO0
    lj.pwm.start(
        channel='DIO0', 
        frequency = freq,
        duty_cycle = duty
    )

    lj.stream.input(
        'DIO0',
        scan_rate=1000,
        scans_per_read=100
    )
    data = lj.stream.read()
    lj.stream.stop()
    lj.pwm.stop()

    _plot_stream(data)


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

if __name__ == "__main__":
    main()
