from labjack import ljm
import numpy as np
from datetime import datetime
from .channels import StreamChannel
from labjackt7 import channels

'''
Streaming 

Streaming requires a single scan rate (and clock and trigger source).

Up to 128 channels can be scanned while streaming.
Up to 4 channels can be outputs (limited by stream buffers).
Total output buffer size is 64k (of UINT16 words), by default each channel gets 16k.


Outputs are prepared with LJM_PeriodicStreamOut, which connects an output port (target) with data buffer (stream_out_index).
LJM_PeriodicStreamOut(
    int Handle,
    int StreamOutIndex,
    int TargetAddr,
    double ScanRate,
    int NumValues,
    const double * aWriteData)

'''


class StreamConfig():
    def __init__(self, scan_rate:int=100000, reads_per_scan:int=1, settling_time:int=0, resolution_index:int=0, clock_source:int=0):
        self.scan_rate:int = scan_rate
        self.reads_per_scan:int = reads_per_scan
        self.settling_time:int = settling_time
        self.resolution_index:int = resolution_index
        self.clock_source:int = clock_source
        self.scan_list = []

    def to_dict(self):
        return {
            'SCAN_RATE': self.scan_rate,
            'READS_PER_SCAN': self.reads_per_scan,
            'STREAM_SETTLING_US': self.settling_time,
            'STREAM_RESOLUTION_INDEX': self.resolution_index,
            'STREAM_CLOCK_SOURCE': self.clock_source,
        }


class Stream():
    def __init__(self, labjack):
        self.labjack = labjack
        self.stop()

        self.scan_rate:int          = self._device_scanRate()
        self.reads_per_scan:int     = 1
        self.settling_time:int      = 0
        self.resolution_index:int   = 0
        self.clock_source:int       = 0 
        self.stream_buffer_size:int|None = None # default 4096, max 32768
#         ljm.eWriteName(handle, "STREAM_TRIGGER_INDEX", 0)

        self.scan_list:list       = []
        self.configure(
            scan_rate=self.scan_rate,
            reads_per_scan=self.reads_per_scan,
            settling_time=self.settling_time,
            resolution_index=self.resolution_index,
            clock_source=self.clock_source,
            stream_buffer_size=self.stream_buffer_size
        
        ) # set defaults

    def configure(self, 
            scan_rate:int|None=None, 
            reads_per_scan:int|None=None, 
            settling_time:int|None=None, 
            resolution_index:int|None=None, 
            clock_source:int|None=None,
            stream_buffer_size:int|None=None
        ):
        if scan_rate is not None:
            self.scan_rate = scan_rate
            # this is applied by start()
        if reads_per_scan is not None:
            self.reads_per_scan = reads_per_scan
            # this is applied by ??
        if settling_time is not None:
            self.settling_time = settling_time
            ljm.eWriteName(self.labjack.handle, "STREAM_SETTLING_US", self.settling_time)
        if resolution_index is not None:
            self.resolution_index = resolution_index
            ljm.eWriteName(self.labjack.handle, "STREAM_RESOLUTION_INDEX", self.resolution_index)
        if clock_source is not None:
            self.clock_source = clock_source
            ljm.eWriteName(self.labjack.handle, "STREAM_CLOCK_SOURCE", self.clock_source)
        if stream_buffer_size is not None:
            if stream_buffer_size > 32768:
                raise ValueError("Stream buffer size must be <= 32768")
            self.stream_buffer_size = stream_buffer_size
            ljm.eWriteName(self.labjack.handle, "STREAM_BUFFER_SIZE_BYTES", self.stream_buffer_size)


    def start(self) -> float:
        self.stop()

        actual_scan_rate = ljm.eStreamStart(
            handle = self.labjack.handle,
            scansPerRead = self.scan_rate // self.reads_per_scan,
            numAddresses = len(self.scan_list),
            aScanList = self.scan_list,
            scanRate = self.scan_rate
        )
        return actual_scan_rate


    def stop(self):
        ''' Stop streaming if currently running '''
        try:
            ljm.eStreamStop(self.labjack.handle)
        except:
            pass


    def read(self):
        aData, deviceScanBacklog, ljmScanBacklog = ljm.eStreamRead(self.labjack.handle)
        # print(f"Stream Read: {len(aData)} samples, deviceScanBacklog={deviceScanBacklog}, ljmScanBacklog={ljmScanBacklog}")
        return aData


    def add_output(self, 
            target:StreamChannel|str, 
            data:list, 
            stream_out_index:int = 0,
        ):
        ''' 
        Setup a periodic output stream on output device 'target' using buffer stream_out_index.

        This supports generic targets, DAC0/1, FIO_STATE/DIRECTION (aka the whole FIO buffer)
        Supported targets are enumerated in .channels.StreamChannel

        Use configure() to setup scan_rate and clock source
        '''
        self.stream_out_index = stream_out_index

        target_addr = ljm.nameToAddress(target)[0]
        scan_addr   = ljm.nameToAddress(f'STREAM_OUT{stream_out_index}')[0]
        self.scan_list.append(scan_addr)

        if (self.scan_rate <= 0) or (self.scan_rate > self._device_scanRate()*len(self.scan_list)):
            print(f'WARNING: ScanRate {self.scan_rate} for {len(self.scan_list)} channels is invalid')

        ljm.periodicStreamOut(
            handle         = self.labjack.handle,
            streamOutIndex = stream_out_index,
            targetAddr     = target_addr,
            scanRate       = self.scan_rate,
            numValues      = len(data),
            aWriteData     = data,
        ) 
        return
    

    def add_outputs(self, targets:list[StreamChannel|str], data:list[list], stream_out_indexes:list[int]):
        if (len(data) != len(targets)) or (len(data) != len(stream_out_indexes)):
            raise ValueError("Length of data, targets, and stream_out_indexes must match")
        for t, d, i in zip(targets, data, stream_out_indexes):
            self.add_output(t, d, i)
        return


    def add_input(self, channel:int|str|StreamChannel):
        ''' 
        Setup a periodic input stream on output device 'channel'.

        This supports generic targets, AIN0-n, FIO_STATE/DIRECTION (aka the whole FIO buffer)
        Supported targets are enumerated in .channels.StreamChannel

        Use config to setup scan rate,a reads per scan, settling time, resolution index, and clock source.
        '''
        scan_list = []
        self.scan_list.append(ljm.nameToAddress(self._chan_to_ain(channel))[0])

#         aNamesValues = {
#             "AIN_ALL_NEGATIVE_CH" : ljm.constants.GND,
#             "AIN0_RANGE" : 10.0,
#             "AIN1_RANGE" : 10.0,
#             "AIN2_RANGE" : 10.0,
#             "AIN3_RANGE" : 10.0,
#         }
#         numFrames = len(aNamesValues)
#         ljm.eWriteNames(handle, numFrames, list(aNamesValues.keys()), list(aNamesValues.values()))


        return


    def add_inputs(self, channels:list[int]|list[str]|list[StreamChannel]):
        for ch in channels:
            self.add_input(ch)
        return
    

    def ain(self, 
            channels:str|int|StreamChannel|list[str]|list[int]|list[StreamChannel], 
            scan_rate:int|None=None,
            reads_per_scan:int|None=None,
            settling_time:int|None=None,
            resolution_index:int|None=None,
            clock_source:int|None=None,
            #range:int|None=None
        ):
        '''
        ain() simple analog streaming input.
        Available channels are AIN0 and AINx.  
        '''

        scan_list = []
        if channels is not None and isinstance(channels, list):
            for c in channels:
                scan_list.append(ljm.nameToAddress(self._chan_to_ain(c))[0])
        elif channels is not None:
            scan_list = [ljm.nameToAddress(self._chan_to_ain(channels))[0]]
        self.scan_list = scan_list

        self.configure(scan_rate, reads_per_scan, settling_time, resolution_index, clock_source)
        self.start()
        
        return

    def aout(self, 
            channels:str|int|StreamChannel|list[str]|list[int]|list[StreamChannel],
            data:list,
            scan_rate:int|None=None,
            clock_source:int|None=None,
            loop:int=0,
        ):

        ''' 
        aout() simple analog streaming output.
        Available channels are DAC0 and DAC1.
        Data should be one list of data per channel.

        Leave parameters as None to use the current configuration.
        '''
        if isinstance(channels, (int, str)):
            _channels = [channels]
            _data = [data]
        elif isinstance(data, list) and len(data) == len(channels):
            _channels = channels
            _data = data
        else:
            raise ValueError("Analog stream-out data must have one column per output channel.")

        self.configure(scan_rate=scan_rate, clock_source=clock_source)
        # todo LOOP
        for i, ch in enumerate(_channels):
            self.add_output(_data[i], self._chan_to_dac(ch), stream_out_index=i)

        actual_scan_rate = self.start()
        return actual_scan_rate

    def dout(self, 
            channels:str|int|list[str|int],
            data:list,
            scan_rate:int|None=None,
            loop=0,
        ):
        ''' 
        dout simple digital output streaming
        (e.g. FIO0) into the full-port bitmask and direction used by the stream engine.
        '''
        if isinstance(channels, (int, str)):
            _channels = [channels]
            _data = [data]
        elif isinstance(data, list) and len(data) == len(channels):
            _channels = channels
            _data = data
        else:
            raise ValueError("Analog stream-out data must have one column per output channel.")

        self.configure(scan_rate=scan_rate)

        for i, ch in enumerate(_channels):
            self.add_output(_data[i], self._chan_to_dio(ch), stream_out_index=i)

        return


    def stream_burst(self, aScanListNames:list, scanRate:int=0, scanTime_s:float=1) -> tuple[float,list]:
        ''' 
            Args:
                scanListNames: ["AIN0", "AIN1" ...] 
                scan_rate: 0 for max rate
                scan_time_s: number of seconds to sample (default 1)
        '''

        '''
        A scan is a single sample on a single channel.
        When mutliple channels are to be collected, 
        the channels are stepped through in list order with one sample
        (aka scan) collected.
        This, the [per-channel]scan rate is provided scanRate/len(scanListNames)
        '''
        aScanListNames = [self._chan_to_ain(ch) for ch in aScanListNames]
        aScanList = ljm.namesToAddresses(len(aScanListNames), aScanListNames)[0]  # Names to addresses for streamBurst
        if (scanRate <= 0) or (scanRate > self._device_scanRate()):
            scanRate = self._device_scanRate()
        num_scans = int(scanTime_s*scanRate)  # Number of scans to perform
        num_scans = num_scans - (num_scans % len(aScanList)) # ensure all channels have equal samples
        start = datetime.now()
        actual_scan_rate, aData = ljm.streamBurst(
            self.labjack.handle, 
            len(aScanList), 
            aScanList, 
            float(scanRate), 
            int(num_scans))
        end = datetime.now()
        if False:
            print(f"Channels: {len(aScanListNames)},  Samples per Ch: {len(aData)/len(aScanListNames)}, ScanRate: {scanRate}, Elapsed Time = {(end - start).seconds + float((end - start).microseconds) / 1000000}s" )
        if aData.count(-9999.0) > 0:
            print(f"WARNING: some samples were skipped! Total skips, all channels) = f{aData.count(-9999.0)}")
        return actual_scan_rate, self._reshape_data(aData, len(aScanList))


    def set_trigger(self, ch):
        if ch is None:
            self.labjack._command("STREAM_TRIGGER_INDEX", 0) # disable triggered stream
        else:
            self.labjack._write_dict({
                f"DIO{ch}_EF_ENABLE": 0
            })
            self.labjack._write_dict({
                f"DIO{ch}_EF_INDEX": 3,
                f"DIO{ch}_EF_OPTIONS": 12,   ## current value: 0 (PWM Out)
                # f"DIO{ch}_EF_VALUE_A": 2,
                f"DIO{ch}_EF_CONFIG_A": 1,
                f"DIO{ch}_EF_CONFIG_B": 1,
                f"DIO{ch}_EF_ENABLE": 1,
                "STREAM_TRIGGER_INDEX": 2000+ch
            })
            ljm.writeLibraryConfigS('LJM_STREAM_RECEIVE_TIMEOUT_MS',0)  #disable timeout

    def _device_scanRate(self) -> int:
        if self.labjack.device_type == ljm.constants.dtT7:
            return 100000
        # elif self.labjack.device_type == ljm.constants.dtT4:
        #     return 40000
        raise ValueError("ERROR - device type must be T7")


    def _reshape_data(self, aData:list, num_channels:int):
        ''' splits scan data into list of lists'''
        channels = []
        ch = []
        for i in range(num_channels):
            ch = aData[i:][::num_channels]
            channels.append(ch)
        return channels


    def _write_config(self, stream_options: dict | StreamConfig):
        self.stop()
        if isinstance(stream_options, StreamConfig):
            self.labjack._write_dict(stream_options.to_dict())
        else:
            self.labjack._write_dict(stream_options)


    def _set_inhibit(self, channels):
        bitmask = self.labjack.digital.bitmask(channels)
        inhibit = 0x7FFFFF-bitmask

        self.labjack._write_dict({
            'DIO_INHIBIT': inhibit,
            'DIO_DIRECTION': bitmask
        })

    #todo: access these from the analog module
    def _chan_to_ain(self, channel):
        if type(channel) is int:
            channel = f'AIN{channel}'
        return channel
    
    def _chan_to_dac(self, channel):
        if type(channel) is int:
            channel = f'DAC{channel}'
        return channel

    #todo access this from the digital module
    def _chan_to_dio(self, channel):
        if isinstance(channel,  int):
            channel = f'DIO{channel}'
        return channel