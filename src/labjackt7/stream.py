from labjack import ljm
import numpy as np
from dataclasses import dataclass
from datetime import datetime
from .channels import StreamChannel, StreamOutChannel

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
        self.scans_per_read:int = scan_rate
        self.settling_time:int = settling_time
        self.resolution_index:int = resolution_index
        self.clock_source:int = clock_source
        self.scan_list = []

    def to_dict(self):
        return {
            'SCAN_RATE': self.scan_rate,
            'SCANS_PER_READ': self.scans_per_read,
            'STREAM_SETTLING_US': self.settling_time,
            'STREAM_RESOLUTION_INDEX': self.resolution_index,
            'STREAM_CLOCK_SOURCE': self.clock_source,
        }


@dataclass(slots=True)
class StreamChannelInfo:
    target: int | str | StreamChannel
    target_addr: int
    data_size: int
    stream_out_index: int
    scan_index: int


class Stream():
    def __init__(self, labjack):
        self.labjack = labjack
        self.stop()

        self.scan_rate:int          = 0
        self.scans_per_read:int     = 1
        self.settling_time:int      = 0
        self.resolution_index:int   = 0
        self.clock_source:int       = 0 
        self.stream_buffer_size:int|None = None # default 4096, max 32768
        self.stream_trigger_index = 0 #todo: implement   ljm.eWriteName(handle, "STREAM_TRIGGER_INDEX", 0)

        self.scan_list:list       = []
        self.details:list[StreamChannelInfo] = []
        self.configure(
            scan_rate=self.scan_rate,
            scans_per_read=self.scans_per_read,
            settling_time=self.settling_time,
            resolution_index=self.resolution_index,
            clock_source=self.clock_source,
            stream_buffer_size=self.stream_buffer_size
        
        ) # set defaults

    def configure(self, 
            scan_rate:int|None=None, 
            scans_per_read:int|None=None, 
            settling_time:int|None=None, 
            resolution_index:int|None=None, 
            clock_source:int|None=None,
            stream_buffer_size:int|None=None
        ):
        if scan_rate is not None:
            self.scan_rate = scan_rate # this is applied by start()
        if scans_per_read is not None:
            self.scans_per_read = scans_per_read # this is applied by ??
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

        if self.scan_rate == 0:
            raise ValueError("Scan rate must be > 0")
        # if self.scans_per_read == 1 or self.scans_per_read > self.scan_rate:
        #     raise ValueError("Set scans per read")

        actual_scan_rate = ljm.eStreamStart(
            handle = self.labjack.handle,
            scansPerRead = self.scans_per_read,
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


    def read(self, verbose=False):
        aData, deviceScanBacklog, ljmScanBacklog = ljm.eStreamRead(self.labjack.handle)
        if verbose:
            print(f"Stream Read: {len(aData)} samples, deviceScanBacklog={deviceScanBacklog}, ljmScanBacklog={ljmScanBacklog}")
        shaped_data = self._reshape_data(aData, len(self.scan_list))
        return shaped_data


    def add_output(self, 
            target:StreamOutChannel|str|int, 
            data:list|np.ndarray, 
            stream_out_index:int = 0,
            loop:int = 1
        ):
        ''' 
        Setup a periodic output stream on output device 'target' using buffer stream_out_index.

        This supports generic targets, DAC0/1, FIO_STATE/DIRECTION (aka the whole FIO buffer)
        Supported targets are enumerated in .channels.StreamChannel

        Use configure() to setup scan_rate and clock source
        '''
        self.stop()

        if len(data) > 16384:
            raise ValueError('Stream output data cannot exceed 16384 values')
        if isinstance(data, np.ndarray):
            data = data.tolist()

        target_addr = ljm.nameToAddress(target)[0]
        scan_addr   = ljm.nameToAddress(f'STREAM_OUT{stream_out_index}')[0]
        self.scan_list.append(scan_addr)

        if (self.scan_rate <= 0):
            raise ValueError(f'WARNING: ScanRate {self.scan_rate} for {len(self.scan_list)} channels is invalid')
        if (self.scan_rate > self._device_scanRate()*len(self.scan_list)):
            raise ValueError(f'WARNING: ScanRate {self.scan_rate} for {len(self.scan_list)} channels exceeds max {self._device_scanRate()}')

        i = stream_out_index
        buffer_size = 1 << (2 * len(data)).bit_length()
        # buffer_size = 16384
        ljm.eWriteName(self.labjack.handle, f'STREAM_OUT{i}_ENABLE', 0)
        aSetup = {
            f'STREAM_OUT{i}_TARGET': target_addr,
            f'STREAM_OUT{i}_BUFFER_ALLOCATE_NUM_BYTES': buffer_size,
            f'STREAM_OUT{i}_ENABLE': 1,
            f'STREAM_OUT{i}_LOOP_NUM_VALUES': len(data),
        }
        ljm.eWriteNames(self.labjack.handle,
            len(aSetup), aSetup.keys(), aSetup.values())
        if isinstance(data[0], float):
            ljm.eWriteNameArray(self.labjack.handle,
                f'STREAM_OUT{i}_BUFFER_F32', len(data), data)
        elif isinstance(data[0], int):
            ljm.eWriteNameArray(self.labjack.handle,
                f'STREAM_OUT{i}_BUFFER_U16', len(data), data)
        else:
            raise TypeError('Data must be float or int type')
        ljm.eWriteName(self.labjack.handle, 
            f'STREAM_OUT{i}_SET_LOOP', loop)

        self.details.append(
            StreamChannelInfo(
                stream_out_index=stream_out_index,
                scan_index = len(self.scan_list)-1,
                target = target,
                target_addr = target_addr,
                data_size = len(data)
            )
        )
        return
    

    def add_outputs(self, 
            targets:list[StreamOutChannel]|list[str]|list[int], 
            data:list[list], 
            stream_out_indexes:list[int]
        ):
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
        self.scan_list.append(ljm.nameToAddress(self._chan_to_ain(channel))[0])
        return


    def add_inputs(self, channels:list[int]|list[str]|list[StreamChannel]):
        for ch in channels:
            self.add_input(ch)
        return
    

    def ain(self, 
            channels:str|int|StreamChannel|list[str]|list[int]|list[StreamChannel], 
            scan_rate:int|None=None,
            scans_per_read:int|None=None,
            settling_time:int|None=None,
            resolution_index:int|None=None,
            clock_source:int|None=None,
            range:int|list[int]|None=None
        ):
        '''
        ain() simple analog streaming input.
        Available channels are AINx.  
        This is similar to stream.input(), 
        but it will accept channel as integer x for AINx
        and set channel ranges.
        '''

        _channels = []
        if isinstance(channels, list):
            _channels:list[str] = [self._chan_to_ain(c) for c in channels]
        else:
            _channels:list[str] = [self._chan_to_ain(channels)]

        #TODO: Set channel ranges
        if range is not None:
            print("Setting range not yet supported")

        return self.input(
            _channels,
            scan_rate=scan_rate,
            scans_per_read=scans_per_read,
            settling_time=settling_time,
            resolution_index=resolution_index,
            clock_source=clock_source,

        ) 

    def aout(self, 
            channels:str|int|StreamOutChannel|list[str]|list[int]|list[StreamOutChannel],
            data:list|np.ndarray,
            scan_rate:int|None=None,
            clock_source:int|None=None,
            loop:int=0,
        ):

        ''' 
        aout() simple analog streaming output.
        Available channels are DAC0 and DAC1.
        Data should be one list (or array) of data per channel.

        Leave parameters as None to use the current configuration.
        '''
        if isinstance(channels, (int, str, StreamOutChannel)):
            _channels = [channels]
            _data = [data]
        elif isinstance(data, np.ndarray):
            _channels = channels
            _data = data#.tolist()
        elif isinstance(data, list):
            _channels = channels
            _data = data
        else:
            raise ValueError("Analog stream-out data must have one column per output channel.")

        #_data = [d.tolist() if isinstance(d, np.ndarray) else d for d in _data]
        if len(_data) != len(_channels):
            raise ValueError("Analog stream-out data must have one column per output channel.")

        _stream_indeces = list(range(len(_channels)))
        self.configure(scan_rate=scan_rate, clock_source=clock_source)
        self.add_outputs(_channels, _data, stream_out_indexes=_stream_indeces)

        actual_scan_rate = self.start()
        return actual_scan_rate


    def input(self, 
            channels:str|StreamChannel|list[str]|list[StreamChannel], 
            scan_rate:int|None=None,
            scans_per_read:int|None=None,
            settling_time:int|None=None,
            resolution_index:int|None=None,
            clock_source:int|None=None,
            #range:int|None=None
        ):
        '''
        Stream streaming input, analog or digital.
        Available channels are AIN0 and AINx.  
        Digital channels are and DIOx or *IO_STATE.
        '''

        scan_list = []
        if isinstance(channels, list):
            scan_list = [ljm.nameToAddress(c)[0] for c in channels]
        elif isinstance(channels, (str,StreamChannel)):
            scan_list = [ljm.nameToAddress(channels)[0]]
        self.scan_list = scan_list

        self.configure(scan_rate, scans_per_read, settling_time, resolution_index, clock_source)
        actuatal_scan_rate = self.start()
        return actuatal_scan_rate 

    def dout(self, 
            channels:str|int|StreamOutChannel|list[str]|list[int]|list[StreamOutChannel],
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
            raise ValueError("Stream-out data must have one column per output channel.")

        self.configure(scan_rate=scan_rate)

        for i, ch in enumerate(_channels):
            self.add_output(
                self._chan_to_dio(ch),
                _data[i], 
                stream_out_index=i)

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

    def _chan_to_ain(self, channel) -> str:
        if isinstance(channel, int):
            channel = f'AIN{channel}'
        if isinstance(channel, StreamChannel):
            channel = str(channel)
        return channel
    
    def _chan_to_dac(self, channel) -> str:
        if isinstance(channel, int):
            channel = f'DAC{channel}'
        if isinstance(channel, StreamOutChannel):
            channel = str(channel)
        return channel

    def _chan_to_dio(self, channel) -> str:
        if isinstance(channel,  int):
            channel = f'DIO{channel}'
        if isinstance(channel, StreamChannel) or isinstance(channel, StreamOutChannel):
            channel = str(channel)
        return channel
