import { Link } from 'react-router-dom';
import { 
  Scale, FileText, Mic, Users, ChevronRight, 
  Shield, Clock, Globe, BookOpen, Gavel, Phone 
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

const features = [
  {
    icon: Mic,
    title: 'Voice Input',
    description: 'Speak your legal query in English, Hindi, or Telugu using voice recognition.',
    color: 'text-orange-500',
    bg: 'bg-orange-50'
  },
  {
    icon: Scale,
    title: 'Instant Legal Guidance',
    description: 'Get immediate guidance on FIR, RTI, consumer rights, labour law, and more.',
    color: 'text-blue-500',
    bg: 'bg-blue-50'
  },
  {
    icon: FileText,
    title: 'Document Generation',
    description: 'Auto-generate FIR and RTI application templates in multiple languages.',
    color: 'text-emerald-500',
    bg: 'bg-emerald-50'
  },
  {
    icon: Users,
    title: 'Internship Portal',
    description: 'Law students can register for internships and assist citizens with legal matters.',
    color: 'text-purple-500',
    bg: 'bg-purple-50'
  }
];

const legalCategories = [
  { icon: Shield, label: 'FIR / Police Complaints', desc: 'File criminal complaints' },
  { icon: BookOpen, label: 'Right to Information', desc: 'RTI applications' },
  { icon: Gavel, label: 'Consumer Rights', desc: 'Product & service disputes' },
  { icon: Users, label: 'Labour Law', desc: 'Employment issues' },
  { icon: Shield, label: 'Family Matters', desc: 'Divorce, maintenance, domestic issues' },
  { icon: FileText, label: 'Property Disputes', desc: 'Land & ownership issues' },
];

export default function HomePage() {
  return (
    <div className="page-enter page-enter-active" data-testid="home-page">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-slate-900 noise-texture">
        {/* Background Image with Overlay */}
        <div className="absolute inset-0">
          <img
            src="https://images.unsplash.com/photo-1716483081614-d9053f2f2801?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwzfHxpbmRpYW4lMjBzdXByZW1lJTIwY291cnQlMjBidWlsZGluZyUyMGFyY2hpdGVjdHVyZXxlbnwwfHx8fDE3NjY1MDcwNjN8MA&ixlib=rb-4.1.0&q=85"
            alt="Indian Supreme Court"
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 hero-gradient" />
        </div>

        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 lg:py-32">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-black text-white leading-tight mb-6">
                Intelligent Legal Aid
                <span className="text-orange-500"> System</span>
              </h1>
              
              <p className="text-slate-300 text-lg leading-relaxed mb-8 max-w-xl">
                A comprehensive platform to help Indian citizens understand their legal rights, 
                get guidance on legal procedures, and generate official documents - all using 
                voice input in English, Hindi, and Telugu.
              </p>
              
              <div className="flex flex-wrap gap-4">
                <Link to="/query">
                  <Button 
                    size="lg" 
                    className="bg-orange-500 hover:bg-orange-600 text-white font-bold px-8 py-6 rounded-md shadow-lg hover:shadow-xl transition-all btn-active"
                    data-testid="get-started-btn"
                  >
                    Submit Legal Query
                    <ChevronRight className="w-5 h-5 ml-1" />
                  </Button>
                </Link>
                <Link to="/students">
                  <Button 
                    size="lg" 
                    variant="outline" 
                    className="border-2 border-white/30 text-white hover:bg-white/10 font-bold px-8 py-6 rounded-md transition-all"
                    data-testid="student-portal-btn"
                  >
                    Student Portal
                  </Button>
                </Link>
              </div>
            </div>

            {/* Stats Card */}
            <div className="hidden lg:block">
              <Card className="bg-white/10 backdrop-blur-md border-white/20">
                <CardContent className="p-8">
                  <h3 className="font-heading font-bold text-white text-xl mb-6">
                    Important Helplines
                  </h3>
                  <div className="space-y-4">
                    <div className="flex items-center gap-4 p-4 rounded-lg bg-white/5">
                      <div className="w-12 h-12 rounded-full bg-orange-500/20 flex items-center justify-center">
                        <Phone className="w-6 h-6 text-orange-500" />
                      </div>
                      <div>
                        <p className="text-white font-bold">15100</p>
                        <p className="text-slate-400 text-sm">NALSA Legal Aid Helpline</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 p-4 rounded-lg bg-white/5">
                      <div className="w-12 h-12 rounded-full bg-pink-500/20 flex items-center justify-center">
                        <Phone className="w-6 h-6 text-pink-500" />
                      </div>
                      <div>
                        <p className="text-white font-bold">181</p>
                        <p className="text-slate-400 text-sm">Women Helpline</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 p-4 rounded-lg bg-white/5">
                      <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center">
                        <Phone className="w-6 h-6 text-blue-500" />
                      </div>
                      <div>
                        <p className="text-white font-bold">1800-11-4000</p>
                        <p className="text-slate-400 text-sm">Consumer Helpline</p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 lg:py-24 bg-white" data-testid="features-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="font-heading text-3xl sm:text-4xl font-bold text-slate-900 mb-4">
              How It Works
            </h2>
            <p className="text-slate-600 max-w-2xl mx-auto">
              Our system uses advanced language processing to understand your legal queries 
              and provide accurate, helpful guidance.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <Card 
                key={index} 
                className="feature-card border-slate-200"
                data-testid={`feature-card-${index}`}
              >
                <CardContent className="p-6">
                  <div className={`w-12 h-12 rounded-lg ${feature.bg} flex items-center justify-center mb-4`}>
                    <feature.icon className={`w-6 h-6 ${feature.color}`} />
                  </div>
                  <h3 className="font-heading font-bold text-lg text-slate-900 mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-slate-600 text-sm leading-relaxed">
                    {feature.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Legal Categories */}
      <section className="py-16 lg:py-24 bg-slate-50" data-testid="categories-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="font-heading text-3xl sm:text-4xl font-bold text-slate-900 mb-4">
              Legal Categories Supported
            </h2>
            <p className="text-slate-600 max-w-2xl mx-auto">
              Get guidance on various legal matters across these categories.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {legalCategories.map((cat, index) => (
              <Link 
                key={index} 
                to="/query" 
                className="flex items-center gap-4 p-4 bg-white rounded-lg border border-slate-200 hover:border-orange-500 hover:shadow-md transition-all group"
                data-testid={`category-${index}`}
              >
                <div className="w-10 h-10 rounded-lg bg-slate-100 group-hover:bg-orange-50 flex items-center justify-center transition-colors">
                  <cat.icon className="w-5 h-5 text-slate-600 group-hover:text-orange-500 transition-colors" />
                </div>
                <div>
                  <h4 className="font-semibold text-slate-900">{cat.label}</h4>
                  <p className="text-sm text-slate-500">{cat.desc}</p>
                </div>
                <ChevronRight className="w-5 h-5 text-slate-400 ml-auto group-hover:text-orange-500 transition-colors" />
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 lg:py-24 bg-slate-900">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="font-heading text-3xl sm:text-4xl font-bold text-white mb-4">
            Ready to Get Legal Guidance?
          </h2>
          <p className="text-slate-400 mb-8 max-w-2xl mx-auto">
            Use our intelligent system to understand your legal rights and get step-by-step 
            guidance on legal procedures. Available in English, Hindi, and Telugu.
          </p>
          <Link to="/query">
            <Button 
              size="lg" 
              className="bg-orange-500 hover:bg-orange-600 text-white font-bold px-12 py-6 rounded-md shadow-lg hover:shadow-xl transition-all btn-active"
              data-testid="cta-btn"
            >
              <Mic className="w-5 h-5 mr-2" />
              Start Speaking Your Query
            </Button>
          </Link>
        </div>
      </section>
    </div>
  );
}
