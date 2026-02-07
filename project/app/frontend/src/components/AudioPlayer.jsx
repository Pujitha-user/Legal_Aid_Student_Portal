import { useState, useRef, useEffect } from 'react';
import { Play, Pause, Volume2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function AudioPlayer({ audioId }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const audioRef = useRef(null);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.addEventListener('loadedmetadata', () => {
        setDuration(audioRef.current.duration);
      });

      audioRef.current.addEventListener('timeupdate', () => {
        setProgress((audioRef.current.currentTime / audioRef.current.duration) * 100);
      });

      audioRef.current.addEventListener('ended', () => {
        setIsPlaying(false);
        setProgress(0);
      });
    }
  }, [audioId]);

  const togglePlay = async () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      setIsLoading(true);
      try {
        await audioRef.current.play();
        setIsPlaying(true);
      } catch (error) {
        console.error('Error playing audio:', error);
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleSeek = (value) => {
    if (audioRef.current && duration) {
      const newTime = (value[0] / 100) * duration;
      audioRef.current.currentTime = newTime;
      setProgress(value[0]);
    }
  };

  const formatTime = (seconds) => {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!audioId) {
    return (
      <div className="text-slate-500 text-sm italic">
        Audio not available
      </div>
    );
  }

  return (
    <div className="flex items-center gap-4 p-4 bg-slate-100 rounded-lg" data-testid="audio-player">
      <audio 
        ref={audioRef} 
        src={`${BACKEND_URL}/api/audio/${audioId}`}
        preload="metadata"
      />
      
      {/* Play/Pause Button */}
      <Button
        size="icon"
        variant="default"
        className="w-12 h-12 rounded-full bg-slate-900 hover:bg-slate-800"
        onClick={togglePlay}
        disabled={isLoading}
        data-testid="audio-play-btn"
        aria-label={isPlaying ? 'Pause' : 'Play'}
      >
        {isLoading ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : isPlaying ? (
          <Pause className="w-5 h-5" />
        ) : (
          <Play className="w-5 h-5 ml-0.5" />
        )}
      </Button>

      {/* Progress Bar */}
      <div className="flex-1 space-y-1">
        <Slider
          value={[progress]}
          onValueChange={handleSeek}
          max={100}
          step={0.1}
          className="cursor-pointer"
          data-testid="audio-progress"
        />
        <div className="flex justify-between text-xs text-slate-500">
          <span>{formatTime((progress / 100) * duration)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>

      {/* Volume Indicator */}
      <Volume2 className="w-5 h-5 text-slate-400" />
    </div>
  );
}
