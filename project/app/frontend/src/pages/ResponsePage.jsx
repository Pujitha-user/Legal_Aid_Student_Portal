import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Volume2, FileText, Loader2, Clock, Tag, Globe } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getCategoryStyle, getCategoryLabel, getLanguageLabel, formatDate } from '@/utils/helpers';
import { toast } from 'sonner';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ResponsePage = () => {
  const { queryId } = useParams();
  const [query, setQuery] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isGeneratingSpeech, setIsGeneratingSpeech] = useState(false);
  const audioRef = useRef(null);

  useEffect(() => {
    const fetchQuery = async () => {
      try {
        const response = await axios.get(`${API}/queries/${queryId}`);
        setQuery(response.data);
      } catch (err) {
        console.error('Error fetching query:', err);
        setError('Failed to load query response');
      } finally {
        setLoading(false);
      }
    };

    if (queryId) {
      fetchQuery();
    }
  }, [queryId]);

  const playTextToSpeech = async () => {
    if (!query?.response_text) return;

    setIsGeneratingSpeech(true);
    try {
      const response = await axios.post(`${API}/text-to-speech`, {
        text: query.response_text,
        language: query.detected_language || 'en'
      }, {
        responseType: 'blob'
      });

      const audioBlob = new Blob([response.data], { type: 'audio/mpeg' });
      const audioUrl = URL.createObjectURL(audioBlob);

      if (audioRef.current) {
        audioRef.current.pause();
      }

      audioRef.current = new Audio(audioUrl);
      audioRef.current.play();
      
      toast.success('Playing audio response...');
    } catch (error) {
      console.error('Error generating speech:', error);
      toast.error('Failed to generate audio. Please try again.');
    } finally {
      setIsGeneratingSpeech(false);
    }
  };

  // Auto-play TTS when query loads (optional, can be removed if not desired)
  useEffect(() => {
    if (query?.response_text && !loading) {
      // Uncomment the line below if you want automatic TTS playback
      // playTextToSpeech();
    }
  }, [query, loading]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-orange-500 mx-auto mb-4" />
          <p className="text-slate-600">Loading response...</p>
        </div>
      </div>
    );
  }

  if (error || !query) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Card className="max-w-md w-full mx-4">
          <CardContent className="p-8 text-center">
            <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-4">
              <FileText className="w-8 h-8 text-red-500" />
            </div>
            <h2 className="font-heading font-bold text-xl text-slate-900 mb-2">
              Query Not Found
            </h2>
            <p className="text-slate-600 mb-6">
              {error || 'The requested query could not be found.'}
            </p>
            <Link to="/query">
              <Button className="bg-slate-900 hover:bg-slate-800">
                Submit New Query
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="page-enter page-enter-active min-h-screen bg-slate-50 py-8 lg:py-12" data-testid="response-page">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Back Button */}
        <Link 
          to="/query" 
          className="inline-flex items-center text-slate-600 hover:text-slate-900 mb-6 transition-colors"
          data-testid="back-btn"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Query Form
        </Link>

        {/* Query Info Card */}
        <Card className="bg-white border-slate-200 shadow-sm mb-6">
          <CardHeader className="border-b border-slate-100">
            <div className="flex flex-wrap items-center gap-3">
              <CardTitle className="font-heading text-lg">Your Query</CardTitle>
              <Badge className={getCategoryStyle(query.category)} data-testid="category-badge">
                <Tag className="w-3 h-3 mr-1" />
                {getCategoryLabel(query.category)}
              </Badge>
              <Badge variant="outline" className="text-slate-600">
                <Globe className="w-3 h-3 mr-1" />
                {getLanguageLabel(query.detected_language)}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-6">
            <p className="text-slate-700 leading-relaxed" data-testid="query-text">
              {query.query_text}
            </p>
            <div className="flex items-center gap-2 mt-4 text-sm text-slate-500">
              <Clock className="w-4 h-4" />
              <span>{formatDate(query.created_at)}</span>
            </div>
          </CardContent>
        </Card>

        {/* Response Card */}
        <Card className="response-card mb-6">
          <CardHeader className="bg-slate-900 text-white">
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <FileText className="w-5 h-5 text-orange-500" />
              Legal Guidance
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6 lg:p-8">
            {/* Response Text */}
            <div 
              className="legal-document prose prose-slate max-w-none mb-8"
              data-testid="response-text"
            >
              <pre className="whitespace-pre-wrap font-body text-slate-700 leading-relaxed text-base">
                {query.response_text}
              </pre>
            </div>

            {/* Audio Player */}
            <div className="border-t border-slate-200 pt-6">
              <h3 className="font-heading font-bold text-slate-900 mb-4 flex items-center gap-2">
                <Volume2 className="w-5 h-5 text-orange-500" />
                Listen to Response
              </h3>
              <div className="flex gap-4">
                <Button
                  onClick={playTextToSpeech}
                  disabled={isGeneratingSpeech}
                  className="flex items-center gap-2"
                >
                  {isGeneratingSpeech ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Volume2 className="w-4 h-4" />
                  )}
                  {isGeneratingSpeech ? 'Generating Audio...' : 'Play Audio Response'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-4 justify-center">
          <Link to="/query">
            <Button 
              size="lg"
              className="bg-orange-500 hover:bg-orange-600 text-white font-bold px-8"
              data-testid="new-query-btn"
            >
              Ask Another Question
            </Button>
          </Link>
          <Link to="/documents">
            <Button 
              size="lg"
              variant="outline"
              className="border-2 border-slate-200 hover:border-slate-900 font-bold px-8"
              data-testid="generate-doc-btn"
            >
              Generate Document
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default ResponsePage;
