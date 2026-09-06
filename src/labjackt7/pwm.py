
_LJ_CLOCK_SPEED = 80e6

'''
Only supported by DIO0/2/3/4/5 (aka FIO0/2/3/4/5).

If a PWM is started before a previous is stopped, 
you may enter an undefined state (especially if you change channels)
To fix this, the buffers should be freed and the clock released.
'''

class PWM:
    def __init__(self, labjack):
        self.labjack = labjack
        self.roll_value:int = 0  # capture roll value for clock roundoff
        self.duty:int = 0
        self.clock_index:int = 0
        self.channel:str = ''
        self.dio_index:int = 0

    def start(self, 
            channel:int|str, 
            frequency:float, 
            duty_cycle:float, 
            clock_index:int=0):
        ''' 
        Starts pulse width modulation on channel that supports PWM OUTPUT.
        Only supported by DIO0/2/3/4/5 (aka FIO0/2/3/4/5)

            Args:
                channel (int): DIO channel to use (0 or 2-5).
                frequency (float): desired frequency in Hz
                duty_cycle (float): duty cycle between 0 and 1.
        '''
        # todo: check that channel supports PWM
        self.channel, self.dio_index = self._pwm_chan_to_dio(channel)
        self.clock_index = clock_index
    
        # set DIO line low before starting
        self.labjack.digital.dout(self.channel, 0)

        _roll_value = int(round(_LJ_CLOCK_SPEED / frequency))
        _duty = duty_cycle * _roll_value
        self.roll_value = int(round(_roll_value))
        self.duty  = int(round(_duty))

        # configure clock source
        config = {
            f"DIO_EF_CLOCK{clock_index}_ENABLE": 0,
            f"DIO_EF_CLOCK{clock_index}_DIVISOR": 1,
            f"DIO_EF_CLOCK{clock_index}_ROLL_VALUE": self.roll_value,
        }
        self.labjack._write_dict(config)

        # enable clock source and tie to output
        config = {
            f"DIO_EF_CLOCK{clock_index}_ENABLE": 1,
            f"{self.channel}_EF_ENABLE": 0,
            f"{self.channel}_EF_INDEX": 0,   # 0 = PWM output, 2 = pulse output
            f"{self.channel}_EF_OPTIONS": 0, # replaced by _EF_CLOCK_SOURCE
            #f"{channel}_EF_CLOCK_SOURCE": 0, # replaced by _EF_CLOCK_SOURCE
            f"{self.channel}_EF_CONFIG_A": self.duty,
        }
        self.labjack._write_dict(config)

        # start pwm
        config = {
            f"{channel}_EF_ENABLE": 1
        }
        self.labjack._write_dict(config)

    def stop(self, channel:int|str|None=None):
        if channel == None:
            channel = self.channel
        dio, index = self._pwm_chan_to_dio(channel)
        self.labjack._command(f"{dio}_EF_ENABLE", 0)
        self.labjack.digital.dout(dio, 0)


    def pulse(self, 
            channel:int|str, 
            frequency:float, 
            duty_cycle:float, 
            count:int=1, 
            clock_source:int=0):
        ''' 
        Generate Pulse stream on an DIO channel that supports PWM OUTPUT.
        Only supported by DIO0/2/3/4/5 (aka FIO0/2/3/4/5)

            Args:
                channel (int): DIO channel to use (0 or 2-5).
                frequency (float): desired frequency in Hz
                duty_cycle (float): duty cycle between 0 and 1.
        '''
        self.channel, self.dio_index  = self._pwm_chan_to_dio(channel)
        self.clock_index = self.clock_index

        # set DIO line low
        self.labjack.digital.dout(self.channel, 0)

        # todo: check roll value is 32 bit for clock0, 16 bit for clock1/2
        # todo: roll value 0 means max roll (2^32 or 2^16)
        # todo: add divisor optimization
        _roll_value = int(round(_LJ_CLOCK_SPEED / frequency))
        _duty = duty_cycle * _roll_value # pulse length counts
        self.roll_value = int(round(_roll_value))
        self.duty  = int(round(_duty))

        # configure clock
        config = {
            f"DIO_EF_CLOCK{clock_source}_ENABLE": 0,
            f"DIO_EF_CLOCK{clock_source}_DIVISOR": 1,
            f"DIO_EF_CLOCK{clock_source}_ROLL_VALUE": self.roll_value,
        }
        self.labjack._write_dict(config)

        # enable clock and tie to output channel
        config = {
            f"DIO_EF_CLOCK{clock_source}_ENABLE": 1,
            f"{self.channel}_EF_ENABLE": 0,
            f"{self.channel}_EF_INDEX": 2,  # 0 = PWM output, 2 = pulse output
            f"{self.channel}_EF_CLOCK_SOURCE": clock_source, # replaced by _EF_CLOCK_SOURCE
            f"{self.channel}_EF_CONFIG_A": self.duty,
            f"{self.channel}_EF_CONFIG_B": 0, # low to high count... for inv or phase??
            f"{self.channel}_EF_CONFIG_C": count,
        }
        self.labjack._write_dict(config)

        # start pulse(s)
        config = {
            f"{channel}_EF_ENABLE": 1
        }
        self.labjack._write_dict(config)
        
    # todo: pulse read
    def pulse_read(self) -> tuple[int, int]:
        '''
        Reads and return tuple[completed pulses, target pulses]

        # DIO#_EF_READ_A: The number of pulses that have been completed.
        # DIO#_EF_READ_B: The target number of pulses.
        '''
        count = self.labjack._query(f"DIO{self.dio_index}_EF_READ_A")
        total = self.labjack._query(f"DIO{self.dio_index}_EF_READ_B")

        return count, total

    # todo: pulse reset
    # DIO#_EF_READ_A_AND_RESET: Reads the number of pulses that have been completed, then restarts the pulse sequence. If the requested number of pulses has not been completed the count will be restarted.

    def _pwm_chan_to_dio(self, channel) -> tuple[str, int]:
        if isinstance(channel, int):
            dio_index = channel
            channel = f'DIO{channel}'
        #todo: expand this to convert FIO/EIO/CIO/MIO to DIO
        elif isinstance(channel, str):
            if channel.upper().startswith("D") or channel.upper().startswith("F"):
                dio_index = int(channel[-1]) # HACK This only works for FIO
                channel = f'DIO{dio_index}'
            else:
                raise ValueError("Only FIO and DIO mapping supported at the moment")
        else:
            raise TypeError("Channel must be int or str")
        return channel, dio_index