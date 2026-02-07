import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Mic, Loader2, Globe, Volume2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { toast } from 'sonner';
import VoiceRecorder from '@/components/VoiceRecorder';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const sampleQueries = {
  en: [
    'How do I file an FIR for theft?',
    'How to apply for RTI to get government information?',
    'My employer is not paying my salary. What can I do?',
    'I bought a defective product. How can I get a refund?',
    'What are my rights in case of domestic violence?',
    'How to resolve a property dispute with neighbor?'
  ],
  hi: [
    'चोरी के लिए एफआईआर कैसे दर्ज करें?',
    'सरकारी सूचना के लिए RTI कैसे लगाएं?',
    'मेरा नियोक्ता वेतन नहीं दे रहा। क्या करें?',
    'मैंने खराब प्रोडक्ट खरीदा। वापसी कैसे मिले?'
  ],
  te: [
    'దొంగతనం కోసం ఎఫ్‌ఐఆర్ ఎలా దాఖలు చేయాలి?',
    'ప్రభుత్వ సమాచారం కోసం RTI ఎలా దరఖాస్తు చేయాలి?',
    'నా యజమాని జీతం ఇవ్వడం లేదు. ఏమి చేయాలి?'
  ]
};

export default function QueryPage() {
  const navigate = useNavigate();
  const [queryText, setQueryText] = useState('');
  const [language, setLanguage] = useState('en');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [voiceResponse, setVoiceResponse] = useState(null);
  const [isPlayingTTS, setIsPlayingTTS] = useState(false);
  const [useVoice, setUseVoice] = useState(false);

  const handleVoiceTranscript = (transcript) => {
    setQueryText(transcript);
  };

  const handleVoiceResponse = async (response) => {
    setVoiceResponse(response);
    setQueryText(response.query_text);
    
    // Auto-play TTS
    try {
      setIsPlayingTTS(true);
      const ttsResponse = await axios.post(`${API}/text-to-speech`, {
        text: response.answer,
        language: response.language
      }, {
        responseType: 'blob'
      });
      
      const audioBlob = new Blob([ttsResponse.data], { type: 'audio/mpeg' });
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.play();
      toast.success('Playing AI response...');
    } catch (error) {
      console.error('TTS error:', error);
      toast.error('Failed to play audio response');
    } finally {
      setIsPlayingTTS(false);
    }
  };

  const handleSampleClick = (sample) => {
    setQueryText(sample);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!queryText.trim()) {
      toast.error('Please enter your legal query');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await axios.post(`${API}/queries`, {
        query_text: queryText,
        language: language
      });
      
      toast.success('Query processed successfully!');
      navigate(`/response/${response.data.id}`);
    } catch (error) {
      console.error('Error submitting query:', error);
      toast.error('Failed to process query. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="page-enter page-enter-active min-h-screen bg-slate-50 py-8 lg:py-12" data-testid="query-page">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="font-heading text-3xl sm:text-4xl font-bold text-slate-900 mb-2">
            Submit Your Legal Query
          </h1>
          <p className="text-slate-600">
            Type or speak your question in English, Hindi, or Telugu
          </p>
        </div>

        {/* Main Form Card */}
        <Card className="bg-white border-slate-200 shadow-sm mb-6">
          <CardHeader className="border-b border-slate-100 pb-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <CardTitle className="font-heading text-xl">Legal Query Form</CardTitle>
              
              {/* Language Selector */}
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4 text-slate-500" />
                <Select value={language} onValueChange={setLanguage}>
                  <SelectTrigger className="w-[140px]" data-testid="language-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en">English</SelectItem>
                    <SelectItem value="hi">हिंदी</SelectItem>
                    <SelectItem value="te">తెలుగు</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-6">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Load Sample Button */}
              <div className="flex justify-end">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const samples = sampleQueries[language];
                    const randomSample = samples[Math.floor(Math.random() * samples.length)];
                    setQueryText(randomSample);
                  }}
                  className="text-slate-600 border-slate-300 hover:bg-slate-50"
                  data-testid="load-sample-btn"
                >
                  Load Sample Query
                </Button>
              </div>
              {/* Input Mode Toggle */}
              <div className="flex gap-2 p-1 bg-slate-100 rounded-lg w-fit">
                <Button
                  type="button"
                  size="sm"
                  variant={!useVoice ? 'default' : 'ghost'}
                  onClick={() => setUseVoice(false)}
                  className={!useVoice ? 'bg-slate-900' : ''}
                  data-testid="text-mode-btn"
                >
                  Type Query
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant={useVoice ? 'default' : 'ghost'}
                  onClick={() => setUseVoice(true)}
                  className={useVoice ? 'bg-slate-900' : ''}
                  data-testid="voice-mode-btn"
                >
                  <Mic className="w-4 h-4 mr-1" />
                  Voice Input
                </Button>
              </div>

              {/* Voice Input */}
              {useVoice && (
                <div className="py-6">
                  <VoiceRecorder 
                    language={language} 
                    onTranscript={handleVoiceTranscript}
                    onVoiceResponse={handleVoiceResponse}
                  />
                </div>
              )}

              {/* Text Input */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Your Legal Query
                </label>
                <Textarea
                  value={queryText}
                  onChange={(e) => setQueryText(e.target.value)}
                  placeholder={language === 'en' 
                    ? 'Describe your legal issue or question here...' 
                    : language === 'hi'
                    ? 'अपना कानूनी मुद्दा या प्रश्न यहां लिखें...'
                    : 'మీ చట్టపరమైన సమస్య లేదా ప్రశ్నను ఇక్కడ వర్ణించండి...'
                  }
                  className="min-h-[150px] resize-none bg-slate-50 border-slate-200 focus:border-slate-900 focus:ring-1 focus:ring-slate-900"
                  data-testid="query-textarea"
                />
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                size="lg"
                disabled={isSubmitting || !queryText.trim()}
                className="w-full bg-orange-500 hover:bg-orange-600 text-white font-bold py-6 rounded-md shadow-lg hover:shadow-xl transition-all btn-active"
                data-testid="submit-query-btn"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Send className="w-5 h-5 mr-2" />
                    Get Legal Guidance
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Voice Response */}
        {voiceResponse && (
          <Card className="bg-white border-slate-200 shadow-sm">
            <CardHeader className="border-b border-slate-100 pb-4">
              <div className="flex items-center justify-between">
                <CardTitle className="font-heading text-lg">AI Legal Response</CardTitle>
                <div className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-slate-500" />
                  <Badge variant="outline">
                    {voiceResponse.language === 'en' ? 'English' : voiceResponse.language === 'hi' ? 'हिंदी' : 'తెలుగు'}
                  </Badge>
                  {isPlayingTTS && (
                    <Badge variant="secondary">
                      <Volume2 className="w-3 h-3 mr-1" />
                      Playing...
                    </Badge>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-6">
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-slate-900 mb-2">Your Query:</h4>
                  <p className="text-slate-700 bg-slate-50 p-3 rounded-md">{voiceResponse.query_text}</p>
                </div>
                <div>
                  <h4 className="font-medium text-slate-900 mb-2">Legal Guidance:</h4>
                  <div className="text-slate-700 bg-slate-50 p-3 rounded-md whitespace-pre-wrap">{voiceResponse.answer}</div>
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={async () => {
                      try {
                        setIsPlayingTTS(true);
                        const ttsResponse = await axios.post(`${API}/text-to-speech`, {
                          text: voiceResponse.answer,
                          language: voiceResponse.language
                        }, {
                          responseType: 'blob'
                        });
                        
                        const audioBlob = new Blob([ttsResponse.data], { type: 'audio/mpeg' });
                        const audioUrl = URL.createObjectURL(audioBlob);
                        const audio = new Audio(audioUrl);
                        audio.play();
                        toast.success('Playing AI response...');
                      } catch (error) {
                        console.error('TTS error:', error);
                        toast.error('Failed to play audio response');
                      } finally {
                        setIsPlayingTTS(false);
                      }
                    }}
                    disabled={isPlayingTTS}
                    variant="outline"
                    size="sm"
                  >
                    <Volume2 className="w-4 h-4 mr-2" />
                    {isPlayingTTS ? 'Playing...' : 'Play Response'}
                  </Button>
                  <Button
                    onClick={() => setVoiceResponse(null)}
                    variant="ghost"
                    size="sm"
                  >
                    Clear
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Sample Queries */}
        <Card className="bg-white border-slate-200 shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="font-heading text-lg">Sample Queries</CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <p className="text-sm text-slate-500 mb-4">
              Click on any sample query to use it:
            </p>
            <div className="flex flex-wrap gap-2">
              {sampleQueries[language].map((sample, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => handleSampleClick(sample)}
                  className="text-left px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm transition-colors"
                  data-testid={`sample-query-${index}`}
                >
                  {sample}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
