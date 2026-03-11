import type { AudioDataPacket } from '@/types'

class AudioPlayer {
  private audioContext: AudioContext | null = null
  private gainNode: GainNode | null = null
  private scriptProcessorNode: ScriptProcessorNode | null = null
  private audioWorkletNode: AudioWorkletNode | null = null

  private audioQueue: ArrayBuffer[] = []
  private isPlaying = false
  private volume = 1.0
  private isMuted = false
  private sampleRate = 44100
  private channels = 2

  private _onStateChange: ((playing: boolean) => void) | null = null

  async init(): Promise<boolean> {
    try {
      this.audioContext = new AudioContext({
        sampleRate: this.sampleRate,
        latencyHint: 'interactive'
      })

      this.gainNode = this.audioContext.createGain()
      this.gainNode.gain.value = this.volume
      this.gainNode.connect(this.audioContext.destination)

      this.scriptProcessorNode = this.audioContext.createScriptProcessor(4096, 0, this.channels)
      
      this.scriptProcessorNode.onaudioprocess = (event) => {
        this.handleAudioProcess(event)
      }

      return true
    } catch (error) {
      console.error('Failed to initialize AudioPlayer:', error)
      return false
    }
  }

  private handleAudioProcess(event: AudioProcessingEvent) {
    if (!this.isPlaying || this.audioQueue.length === 0) {
      const outputBuffer = event.outputBuffer
      for (let channel = 0; channel < outputBuffer.numberOfChannels; channel++) {
        const outputData = outputBuffer.getChannelData(channel)
        outputData.fill(0)
      }
      return
    }

    const outputBuffer = event.outputBuffer
    const samplesNeeded = outputBuffer.length

    let samplesWritten = 0
    const channelData: Float32Array[] = []
    
    for (let channel = 0; channel < outputBuffer.numberOfChannels; channel++) {
      channelData.push(outputBuffer.getChannelData(channel))
    }

    while (samplesWritten < samplesNeeded && this.audioQueue.length > 0) {
      const currentBuffer = this.audioQueue[0]
      const view = new DataView(currentBuffer)
      const samplesInBuffer = currentBuffer.byteLength / (this.channels * 2)
      const samplesToWrite = Math.min(samplesInBuffer, samplesNeeded - samplesWritten)

      for (let i = 0; i < samplesToWrite; i++) {
        for (let channel = 0; channel < this.channels; channel++) {
          const sampleIndex = samplesWritten + i
          const byteIndex = (i * this.channels + channel) * 2
          
          if (byteIndex + 1 < currentBuffer.byteLength) {
            const intSample = view.getInt16(byteIndex, true)
            channelData[channel][sampleIndex] = intSample / 32768.0
          }
        }
      }

      samplesWritten += samplesToWrite

      if (samplesToWrite < samplesInBuffer) {
        const remainingBytes = currentBuffer.byteLength - samplesToWrite * this.channels * 2
        const remainingBuffer = currentBuffer.slice(samplesToWrite * this.channels * 2)
        this.audioQueue[0] = remainingBuffer
      } else {
        this.audioQueue.shift()
      }
    }

    for (let channel = samplesWritten; channel < samplesNeeded; channel++) {
      for (let ch = 0; ch < this.channels; ch++) {
        if (ch < channelData.length && channel < channelData[ch].length) {
          channelData[ch][channel] = 0
        }
      }
    }
  }

  handleAudioData(packet: AudioDataPacket) {
    try {
      const binaryString = atob(packet.data)
      const bytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }

      this.sampleRate = packet.sample_rate
      this.channels = packet.channels

      this.audioQueue.push(bytes.buffer)

      if (!this.isPlaying && this.audioQueue.length > 2) {
        this.startPlayback()
      }
    } catch (error) {
      console.error('Failed to handle audio data:', error)
    }
  }

  startPlayback() {
    if (!this.audioContext || !this.scriptProcessorNode || !this.gainNode) {
      return
    }

    if (this.audioContext.state === 'suspended') {
      this.audioContext.resume()
    }

    this.scriptProcessorNode.connect(this.gainNode)
    this.isPlaying = true
    
    if (this._onStateChange) {
      this._onStateChange(true)
    }
  }

  pausePlayback() {
    this.isPlaying = false
    if (this._onStateChange) {
      this._onStateChange(false)
    }
  }

  resumePlayback() {
    if (this.audioContext && this.audioContext.state === 'suspended') {
      this.audioContext.resume()
    }
    this.isPlaying = true
    if (this._onStateChange) {
      this._onStateChange(true)
    }
  }

  stopPlayback() {
    this.isPlaying = false
    this.audioQueue = []
    
    if (this.scriptProcessorNode) {
      try {
        this.scriptProcessorNode.disconnect()
      } catch (e) {
        // Ignore disconnect errors
      }
    }

    if (this._onStateChange) {
      this._onStateChange(false)
    }
  }

  setVolume(volume: number) {
    this.volume = Math.max(0, Math.min(1, volume))
    if (this.gainNode && !this.isMuted) {
      this.gainNode.gain.value = this.volume
    }
  }

  getVolume(): number {
    return this.volume
  }

  mute() {
    this.isMuted = true
    if (this.gainNode) {
      this.gainNode.gain.value = 0
    }
  }

  unmute() {
    this.isMuted = false
    if (this.gainNode) {
      this.gainNode.gain.value = this.volume
    }
  }

  toggleMute(): boolean {
    if (this.isMuted) {
      this.unmute()
    } else {
      this.mute()
    }
    return this.isMuted
  }

  isMutedState(): boolean {
    return this.isMuted
  }

  getQueueLength(): number {
    return this.audioQueue.length
  }

  getBufferDuration(): number {
    let totalSamples = 0
    for (const buffer of this.audioQueue) {
      totalSamples += buffer.byteLength / (this.channels * 2)
    }
    return totalSamples / this.sampleRate
  }

  onStateChange(callback: (playing: boolean) => void) {
    this._onStateChange = callback
  }

  destroy() {
    this.stopPlayback()
    
    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
    }

    this.gainNode = null
    this.scriptProcessorNode = null
    this.audioWorkletNode = null
    this.audioQueue = []
  }
}

export const audioPlayer = new AudioPlayer()
