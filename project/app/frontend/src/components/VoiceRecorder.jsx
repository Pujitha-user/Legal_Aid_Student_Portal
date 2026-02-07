import { useState, useRef } from 'react';
import { Mic, MicOff, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function VoiceRecorder({ onTranscript, onVoiceResponse, language = 'en' }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isSupported, setIsSupported] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        console.log('Audio blob size:', audioBlob.size, 'type:', audioBlob.type);
        await processAudio(audioBlob);

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
      toast.info('Recording... Click stop when finished');
    } catch (error) {
      console.error('Error starting recording:', error);
      if (error.name === 'NotAllowedError') {
        toast.error('Microphone access denied. Please allow microphone access.');
      } else {
        toast.error('Failed to start recording. Please check your microphone.');
      }
      setIsSupported(false);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsProcessing(true);
      toast.info('Processing audio...');
    }
  };

  const processAudio = async (audioBlob) => {
    try {
      const formData = new FormData();
      formData.append('audio_file', audioBlob, 'recording.webm');
      formData.append('language', language);

      const response = await axios.post(`${API}/voice-query`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      const result = response.data;
      const { query_text, language: detectedLang, answer } = result;
      console.log('Voice query result:', result);

      if (query_text) {
        onTranscript(query_text);
        if (onVoiceResponse) {
          onVoiceResponse({ query_text, language: detectedLang, answer });
        }
        toast.success('Voice processed successfully!');
      } else {
        toast.error('No speech detected. Please try again.');
      }
    } catch (error) {
      console.error('Error processing audio:', error);
      toast.error(`Failed to process audio: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const toggleRecording = () => {
    if (!isSupported) {
      toast.error('Voice recording is not supported in your browser.');
      return;
    }

    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  if (!isSupported) {
    return (
      <div className="text-center p-4 bg-amber-50 rounded-lg border border-amber-200">
        <MicOff className="w-8 h-8 text-amber-500 mx-auto mb-2" />
        <p className="text-sm text-amber-700">
          Voice recording is not supported in your browser. Please use a modern browser with microphone support.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-4" data-testid="voice-recorder">
      {/* Recording Buttons */}
      <div className="flex gap-2">
        <Button
          type="button"
          onClick={startRecording}
          disabled={isRecording || isProcessing}
          className="flex items-center gap-2"
        >
          <Mic className="w-4 h-4" />
          Start
        </Button>
        <Button
          type="button"
          onClick={stopRecording}
          disabled={!isRecording || isProcessing}
          className="flex items-center gap-2"
        >
          <MicOff className="w-4 h-4" />
          Stop
        </Button>
      </div>

      {/* Status Text */}
      <p className={`text-sm font-medium ${
        isProcessing ? 'text-blue-500' : isRecording ? 'text-red-500' : 'text-slate-500'
      }`}>
        {isProcessing ? 'Processing audio...' : isRecording ? 'Recording... Click stop to finish' : 'Click start to speak'}
      </p>
    </div>
  );
}
