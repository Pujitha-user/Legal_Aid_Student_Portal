import { Link } from 'react-router-dom';
import { Scale, Phone, Mail, MapPin } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-slate-900 text-white saffron-border" data-testid="footer">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Logo & About */}
          <div className="md:col-span-2">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-orange-500 rounded-lg flex items-center justify-center">
                <Scale className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="font-heading font-bold text-lg">Legal Aid System</h2>
                <p className="text-xs text-slate-400">Public Assistance Portal</p>
              </div>
            </div>
            <p className="text-slate-400 text-sm leading-relaxed max-w-md">
              An intelligent legal aid and information retrieval system designed to help 
              citizens understand their legal rights and navigate the Indian legal system.
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="font-heading font-bold text-sm uppercase tracking-wider mb-4 text-orange-500">
              Quick Links
            </h3>
            <ul className="space-y-2">
              <li>
                <Link to="/query" className="text-slate-400 hover:text-white text-sm transition-colors">
                  Submit Legal Query
                </Link>
              </li>
              <li>
                <Link to="/students" className="text-slate-400 hover:text-white text-sm transition-colors">
                  Student Internship Portal
                </Link>
              </li>
              <li>
                <Link to="/documents" className="text-slate-400 hover:text-white text-sm transition-colors">
                  Generate Documents
                </Link>
              </li>
            </ul>
          </div>

          {/* Contact Info */}
          <div>
            <h3 className="font-heading font-bold text-sm uppercase tracking-wider mb-4 text-orange-500">
              Helplines
            </h3>
            <ul className="space-y-3">
              <li className="flex items-center gap-2 text-slate-400 text-sm">
                <Phone className="w-4 h-4 text-orange-500" />
                <span>Legal Aid: 15100</span>
              </li>
              <li className="flex items-center gap-2 text-slate-400 text-sm">
                <Phone className="w-4 h-4 text-orange-500" />
                <span>Women: 181</span>
              </li>
              <li className="flex items-center gap-2 text-slate-400 text-sm">
                <Mail className="w-4 h-4 text-orange-500" />
                <span>Consumer: 1800-11-4000</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-8 pt-8 border-t border-slate-800 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-slate-500 text-sm">
            © 2025 Legal Aid System.
          </p>
          <div className="flex items-center gap-4">
            <a href="https://nalsa.gov.in" target="_blank" rel="noopener noreferrer" 
               className="text-slate-500 hover:text-white text-sm transition-colors">
              NALSA
            </a>
            <a href="https://ecourts.gov.in" target="_blank" rel="noopener noreferrer"
               className="text-slate-500 hover:text-white text-sm transition-colors">
              e-Courts
            </a>
            <a href="https://consumerhelpline.gov.in" target="_blank" rel="noopener noreferrer"
               className="text-slate-500 hover:text-white text-sm transition-colors">
              Consumer Portal
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
