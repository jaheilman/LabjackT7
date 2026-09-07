from labjack import ljm
# from .core import LabjackT7

class AnalogConfig():
    def __init__(self, range=10):
        self.analog_config_dict = {
            "AIN_ALL_NEGATIVE_CH" : ljm.constants.GND,
            "AIN_ALL_RANGE" : range
        }
        # other options
        # 'AINx_RANGE'
        # differential():


class Analog():
    def __init__(self, labjack):
        self.labjack = labjack
        self.configure()

    def configure(self, range=10):
        self.labjack._write_dict({
            "AIN_ALL_NEGATIVE_CH" : ljm.constants.GND,
            "AIN_ALL_RANGE" : range
        })

    def ain(self, channel:int|str):
        ''' Read a channel and return the voltage.

            Args:
                channel (int or str): number of the target ADC channel.
        '''
        channel = self._chan_to_ain(channel)
        return self.labjack._query(channel)

    def aout(self, channel:int|str, value:int|float):
        ''' Output an analog voltage.

            Args:
                channel (int or str): number of the target DAC channel.
                value (float): Voltage in volts.
        '''
        channel = self._chan_to_dac(channel)
        self.labjack._command(channel, value)

    # def TDAC(self, channel, value):
    #     ''' Output an analog voltage.

    #         Args:
    #             channel (int): number of the target TDAC channel.
    #             value (float): Voltage in volts.
    #             TDAC (bool): If False, use a DAC channel (0-5 V); if True, use a TDAC channel with the LJTick-DAC accessory (+/-10 V).
    #     '''
    #     self.labjack._command("TDAC%i"%channel, value)


    def _chan_to_ain(self, channel):
        if type(channel) is int:
            channel = f'AIN{channel}'
        return channel
    
    def _chan_to_dac(self, channel):
        if type(channel) is int:
            channel = f'DAC{channel}'
        return channel