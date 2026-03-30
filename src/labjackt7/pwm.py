
# from .core import LabjackT7
_LJ_CLOCK_SPEED = 80e6

class PWM:
    def __init__(self, labjack):
        self.labjack = labjack

    def start(self, channel, frequency, duty_cycle):
        channel = self._chan_to_dio(channel)
        ''' Starts pulse width modulation on an FIO channel.

            Args:
                channel (int): FIO channel to use (0 or 2-5).
                frequency (float): desired frequency in Hz
                duty_cycle (float): duty cycle between 0 and 1.
        '''
        roll_value = _LJ_CLOCK_SPEED / frequency
        config = {
            "DIO_EF_CLOCK0_ENABLE": 0,
            "DIO_EF_CLOCK0_DIVISOR": 1,
            "DIO_EF_CLOCK0_ROLL_VALUE": roll_value,
        }
        self.labjack._write_dict(config)

        config = {
            "DIO_EF_CLOCK0_ENABLE": 1,
            f"{channel}_EF_ENABLE": 0,
            f"{channel}_EF_INDEX": 0,
            f"{channel}_EF_OPTIONS": 0,
            f"{channel}_EF_CONFIG_A": duty_cycle * roll_value,
        }
        self.labjack._write_dict(config)

        config = {
            f"{channel}_EF_ENABLE": 1
        }
        self.labjack._write_dict(config)

    def stop(self, channel):
        channel = self._chan_to_dio(channel)
        self.labjack._command(f"{channel}_EF_ENABLE", 0)
        self.labjack.digital.dout(channel, 0)

    def _chan_to_dio(self, channel):
        if type(channel) is int:
            channel = f'DIO{channel}'
        return channel