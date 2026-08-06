import time

import numpy as np

from labjackt7 import LabjackT7
from labjackt7.channels import StreamChannel


def main():
    pulse_example()

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
        count = 10000
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



if __name__ == "__main__":
    main()
