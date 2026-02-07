import { useState } from 'react';
import { FileText, Download, Loader2, Globe, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function DocumentsPage() {
  const [docType, setDocType] = useState('FIR');
  const [language, setLanguage] = useState('en');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedDoc, setGeneratedDoc] = useState(null);
  
  // FIR Form State
  const [firDetails, setFirDetails] = useState({
    name: '',
    age: '',
    address: '',
    mobile: '',
    email: '',
    incident_date: '',
    incident_time: '',
    incident_place: '',
    incident_description: '',
    accused_details: '',
    witness_details: '',
    evidence_list: ''
  });

  // RTI Form State
  const [rtiDetails, setRtiDetails] = useState({
    name: '',
    address: '',
    mobile: '',
    email: '',
    department_name: '',
    department_address: '',
    question_1: '',
    question_2: '',
    question_3: '',
    period: '',
    fee: '10',
    payment_mode: 'Postal Order'
  });

  const handleGenerateDocument = async () => {
    const details = docType === 'FIR' ? firDetails : rtiDetails;
    
    // Validate required fields
    if (!details.name || !details.address) {
      toast.error('Please fill in at least your name and address');
      return;
    }

    setIsGenerating(true);
    try {
      const response = await axios.post(`${API}/documents`, {
        doc_type: docType,
        language: language,
        details: {
          ...details,
          current_date: new Date().toISOString().split('T')[0],
          place: details.address.split(',')[0] || 'Your City'
        }
      });
      
      setGeneratedDoc(response.data);
      toast.success('Document generated successfully!');
    } catch (error) {
      console.error('Error generating document:', error);
      toast.error('Failed to generate document');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = () => {
    if (!generatedDoc) return;
    
    const blob = new Blob([generatedDoc.content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${docType}_${language}_${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('Document downloaded!');
  };

  return (
    <div className="page-enter page-enter-active min-h-screen bg-slate-50 py-8 lg:py-12" data-testid="documents-page">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="font-heading text-3xl sm:text-4xl font-bold text-slate-900 mb-2">
            Legal Document Generator
          </h1>
          <p className="text-slate-600">
            Generate FIR and RTI application templates in multiple languages
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Form Section */}
          <div>
            <Card className="bg-white border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-100">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <CardTitle className="font-heading">Document Details</CardTitle>
                    <CardDescription>Fill in the details to generate your document</CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    <Globe className="w-4 h-4 text-slate-500" />
                    <Select value={language} onValueChange={setLanguage}>
                      <SelectTrigger className="w-[120px]" data-testid="doc-language-select">
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
                {/* Document Type Tabs */}
                <Tabs value={docType} onValueChange={setDocType} className="space-y-6">
                  <TabsList className="grid grid-cols-2 w-full">
                    <TabsTrigger value="FIR" data-testid="fir-tab">FIR Application</TabsTrigger>
                    <TabsTrigger value="RTI" data-testid="rti-tab">RTI Application</TabsTrigger>
                  </TabsList>

                  {/* FIR Form */}
                  <TabsContent value="FIR" className="space-y-4">
                    <div className="grid sm:grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium text-slate-700">Full Name *</label>
                        <Input
                          value={firDetails.name}
                          onChange={(e) => setFirDetails({ ...firDetails, name: e.target.value })}
                          placeholder="Your full name"
                          data-testid="fir-name-input"
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium text-slate-700">Age</label>
                        <Input
                          value={firDetails.age}
                          onChange={(e) => setFirDetails({ ...firDetails, age: e.target.value })}
                          placeholder="Age in years"
                          data-testid="fir-age-input"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-slate-700">Address *</label>
                      <Input
                        value={firDetails.address}
                        onChange={(e) => setFirDetails({ ...firDetails, address: e.target.value })}
                        placeholder="Your complete address"
                        data-testid="fir-address-input"
                      />
                    </div>
                    <div className="grid sm:grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium text-slate-700">Mobile</label>
                        <Input
                          value={firDetails.mobile}
                          onChange={(e) => setFirDetails({ ...firDetails, mobile: e.target.value })}
                          placeholder="Mobile number"
                          data-testid="fir-mobile-input"
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium text-slate-700">Email</label>
                        <Input
                          type="email"
                          value={firDetails.email}
                          onChange={(e) => setFirDetails({ ...firDetails, email: e.target.value })}
                          placeholder="Email address"
                          data-testid="fir-email-input"
                        />
                      </div>
                    </div>
                    <div className="grid sm:grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium text-slate-700">Incident Date</label>
                        <Input
                          type="date"
                          value={firDetails.incident_date}
                          onChange={(e) => setFirDetails({ ...firDetails, incident_date: e.target.value })}
                          data-testid="fir-date-input"
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium text-slate-700">Incident Time</label>
                        <Input
                          type="time"
                          value={firDetails.incident_time}
                          onChange={(e) => setFirDetails({ ...firDetails, incident_time: e.target.value })}
                          data-testid="fir-time-input"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-slate-700">Incident Place</label>
                      <Input
                        value={firDetails.incident_place}
                        onChange={(e) => setFirDetails({ ...firDetails, incident_place: e.target.value })}
                        placeholder="Where the incident occurred"
                        data-testid="fir-place-input"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-slate-700">Incident Description</label>
                      <Textarea
                        value={firDetails.incident_description}
                        onChange={(e) => setFirDetails({ ...firDetails, incident_description: e.target.value })}
                        placeholder="Describe what happened in detail..."
                        className="min-h-[100px]"
                        data-testid="fir-desc-input"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-slate-700">Accused Details (if known)</label>
                      <Textarea
                        value={firDetails.accused_details}
                        onChange={(e) => setFirDetails({ ...firDetails, accused_details: e.target.value })}
                        placeholder="Name, description, address of accused..."
                        data-testid="fir-accused-input"
                      />
                    </div>
                  </TabsContent>

                  {/* RTI Form */}
                  <TabsContent value="RTI" className="space-y-4">
                    <div>
                      <label className="text-sm font-medium text-slate-700">Full Name *</label>
                      <Input
                        value={rtiDetails.name}
                        onChange={(e) => setRtiDetails({ ...rtiDetails, name: e.target.value })}
                        placeholder="Your full name"
                        data-testid="rti-name-input"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-slate-700">Address *</label>
                      <Input
                        value={rtiDetails.address}
                        onChange={(e) => setRtiDetails({ ...rtiDetails, address: e.target.value })}
                        placeholder="Your complete address"
                        data-testid="rti-address-input"
                      />
                    </div>
                    <div className="grid sm:grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium text-slate-700">Mobile</label>
                        <Input
                          value={rtiDetails.mobile}
                          onChange={(e) => setRtiDetails({ ...rtiDetails, mobile: e.target.value })}
                          placeholder="Mobile number"
                          data-testid="rti-mobile-input"
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium text-slate-700">Email</label>
                        <Input
                          type="email"
                          value={rtiDetails.email}
                          onChange={(e) => setRtiDetails({ ...rtiDetails, email: e.target.value })}
                          placeholder="Email address"
                          data-testid="rti-email-input"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-slate-700">Department Name</label>
                      <Input
                        value={rtiDetails.department_name}
                        onChange={(e) => setRtiDetails({ ...rtiDetails, department_name: e.target.value })}
                        placeholder="Name of the government department"
                        data-testid="rti-dept-input"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-slate-700">Department Address</label>
                      <Input
                        value={rtiDetails.department_address}
                        onChange={(e) => setRtiDetails({ ...rtiDetails, department_address: e.target.value })}
                        placeholder="Address of the department"
                        data-testid="rti-dept-addr-input"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-slate-700">Question 1</label>
                      <Textarea
                        value={rtiDetails.question_1}
                        onChange={(e) => setRtiDetails({ ...rtiDetails, question_1: e.target.value })}
                        placeholder="Your first question/information request..."
                        data-testid="rti-q1-input"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-slate-700">Question 2</label>
                      <Textarea
                        value={rtiDetails.question_2}
                        onChange={(e) => setRtiDetails({ ...rtiDetails, question_2: e.target.value })}
                        placeholder="Your second question (optional)..."
                        data-testid="rti-q2-input"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-slate-700">Question 3</label>
                      <Textarea
                        value={rtiDetails.question_3}
                        onChange={(e) => setRtiDetails({ ...rtiDetails, question_3: e.target.value })}
                        placeholder="Your third question (optional)..."
                        data-testid="rti-q3-input"
                      />
                    </div>
                    <div className="grid sm:grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium text-slate-700">Time Period</label>
                        <Input
                          value={rtiDetails.period}
                          onChange={(e) => setRtiDetails({ ...rtiDetails, period: e.target.value })}
                          placeholder="e.g., Jan 2020 - Dec 2023"
                          data-testid="rti-period-input"
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium text-slate-700">Payment Mode</label>
                        <Select
                          value={rtiDetails.payment_mode}
                          onValueChange={(v) => setRtiDetails({ ...rtiDetails, payment_mode: v })}
                        >
                          <SelectTrigger data-testid="rti-payment-select">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="Postal Order">Postal Order</SelectItem>
                            <SelectItem value="Demand Draft">Demand Draft</SelectItem>
                            <SelectItem value="Court Fee Stamp">Court Fee Stamp</SelectItem>
                            <SelectItem value="Cash">Cash</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>

                {/* Generate Button */}
                <Button
                  onClick={handleGenerateDocument}
                  disabled={isGenerating}
                  className="w-full mt-6 bg-orange-500 hover:bg-orange-600 text-white font-bold py-6"
                  data-testid="generate-doc-btn"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <FileText className="w-5 h-5 mr-2" />
                      Generate {docType} Document
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Preview Section */}
          <div>
            <Card className="bg-white border-slate-200 shadow-sm sticky top-24">
              <CardHeader className="border-b border-slate-100">
                <div className="flex items-center justify-between">
                  <CardTitle className="font-heading">Document Preview</CardTitle>
                  {generatedDoc && (
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={handleDownload}
                      data-testid="download-doc-btn"
                    >
                      <Download className="w-4 h-4 mr-2" />
                      Download
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="p-6">
                {generatedDoc ? (
                  <div className="document-preview" data-testid="doc-preview">
                    {generatedDoc.content}
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <FileText className="w-16 h-16 text-slate-200 mx-auto mb-4" />
                    <p className="text-slate-500">
                      Fill in the details and click Generate to see your document preview
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Info Card */}
            <Card className="bg-amber-50 border-amber-200 mt-4">
              <CardContent className="p-4 flex gap-3">
                <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-amber-800">
                  <p className="font-medium">Important Note</p>
                  <p className="mt-1">
                    This is a template document. Please verify all details and consult with a legal 
                    professional before submitting any official application.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
