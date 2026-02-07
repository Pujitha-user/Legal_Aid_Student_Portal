import { useState, useEffect } from 'react';
import { Users, Briefcase, Plus, Trash2, Loader2, GraduationCap, Mail, Building } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { getStatusStyle, getCategoryLabel, formatDate } from '@/utils/helpers';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function StudentPortal() {
  const [students, setStudents] = useState([]);
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [studentDialogOpen, setStudentDialogOpen] = useState(false);
  const [caseDialogOpen, setCaseDialogOpen] = useState(false);
  
  // Form states
  const [newStudent, setNewStudent] = useState({ name: '', email: '', college: '', skills: '' });
  const [newCase, setNewCase] = useState({ title: '', description: '', category: 'consumer' });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [studentsRes, casesRes] = await Promise.all([
        axios.get(`${API}/students`),
        axios.get(`${API}/cases`)
      ]);
      setStudents(studentsRes.data);
      setCases(casesRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSeedData = async () => {
    try {
      await axios.post(`${API}/seed`);
      toast.success('Sample data loaded successfully!');
      fetchData();
    } catch (error) {
      toast.error('Failed to seed data');
    }
  };

  const handleAddStudent = async (e) => {
    e.preventDefault();
    
    // Validation
    if (!newStudent.name.trim()) {
      toast.error('Please enter student name');
      return;
    }
    if (!newStudent.email.trim()) {
      toast.error('Please enter email address');
      return;
    }
    if (!newStudent.email.includes('@')) {
      toast.error('Please enter a valid email address');
      return;
    }
    if (!newStudent.college.trim()) {
      toast.error('Please enter college name');
      return;
    }
    
    try {
      const skillsArray = newStudent.skills.split(',').map(s => s.trim()).filter(Boolean);
      await axios.post(`${API}/students`, {
        ...newStudent,
        skills: skillsArray
      });
      toast.success('Student added successfully!');
      setStudentDialogOpen(false);
      setNewStudent({ name: '', email: '', college: '', skills: '' });
      fetchData();
    } catch (error) {
      console.error('Error adding student:', error);
      toast.error('Failed to add student. Please try again.');
    }
  };

  const handleDeleteStudent = async (studentId) => {
    if (!window.confirm('Are you sure you want to delete this student?')) return;
    try {
      await axios.delete(`${API}/students/${studentId}`);
      toast.success('Student deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete student');
    }
  };

  const handleAddCase = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/cases`, newCase);
      toast.success('Case added successfully!');
      setCaseDialogOpen(false);
      setNewCase({ title: '', description: '', category: 'consumer' });
      fetchData();
    } catch (error) {
      toast.error('Failed to add case');
    }
  };

  const handleAssignCase = async (caseId, studentId) => {
    try {
      await axios.patch(`${API}/cases/${caseId}`, {
        assigned_student_id: studentId,
        status: 'assigned'
      });
      toast.success('Case assigned successfully!');
      fetchData();
    } catch (error) {
      toast.error('Failed to assign case');
    }
  };

  const handleDeleteCase = async (caseId) => {
    if (!window.confirm('Are you sure you want to delete this case?')) return;
    try {
      await axios.delete(`${API}/cases/${caseId}`);
      toast.success('Case deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete case');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Loader2 className="w-12 h-12 animate-spin text-orange-500" />
      </div>
    );
  }

  return (
    <div className="page-enter page-enter-active min-h-screen bg-slate-50 py-8 lg:py-12" data-testid="student-portal">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="font-heading text-3xl font-bold text-slate-900 mb-1">
              Student Internship Portal
            </h1>
            <p className="text-slate-600">Manage law students and case assignments</p>
          </div>
          <Button 
            variant="outline" 
            onClick={handleSeedData}
            data-testid="seed-data-btn"
          >
            Load Sample Data
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid sm:grid-cols-3 gap-4 mb-8">
          <Card className="bg-white border-slate-200">
            <CardContent className="p-6 flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-blue-50 flex items-center justify-center">
                <Users className="w-6 h-6 text-blue-500" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{students.length}</p>
                <p className="text-sm text-slate-500">Total Students</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-white border-slate-200">
            <CardContent className="p-6 flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-orange-50 flex items-center justify-center">
                <Briefcase className="w-6 h-6 text-orange-500" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{cases.length}</p>
                <p className="text-sm text-slate-500">Total Cases</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-white border-slate-200">
            <CardContent className="p-6 flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-emerald-50 flex items-center justify-center">
                <Briefcase className="w-6 h-6 text-emerald-500" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">
                  {cases.filter(c => c.status === 'assigned').length}
                </p>
                <p className="text-sm text-slate-500">Assigned Cases</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="students" className="space-y-6">
          <TabsList className="bg-white border border-slate-200 p-1">
            <TabsTrigger value="students" className="data-[state=active]:bg-slate-900 data-[state=active]:text-white">
              <Users className="w-4 h-4 mr-2" />
              Students
            </TabsTrigger>
            <TabsTrigger value="cases" className="data-[state=active]:bg-slate-900 data-[state=active]:text-white">
              <Briefcase className="w-4 h-4 mr-2" />
              Cases
            </TabsTrigger>
          </TabsList>

          {/* Students Tab */}
          <TabsContent value="students">
            <Card className="bg-white border-slate-200">
              <CardHeader className="border-b border-slate-100 flex flex-row items-center justify-between">
                <CardTitle className="font-heading">Registered Students</CardTitle>
                <Dialog open={studentDialogOpen} onOpenChange={setStudentDialogOpen}>
                  <DialogTrigger asChild>
                    <Button className="bg-slate-900 hover:bg-slate-800" data-testid="add-student-btn">
                      <Plus className="w-4 h-4 mr-2" />
                      Add Student
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle className="font-heading">Add New Student</DialogTitle>
                    </DialogHeader>
                    <form onSubmit={handleAddStudent} className="space-y-4 mt-4">
                      <div>
                        <label className="text-sm font-medium text-slate-700">Name</label>
                        <Input
                          value={newStudent.name}
                          onChange={(e) => setNewStudent({ ...newStudent, name: e.target.value })}
                          placeholder="Full Name"
                          required
                          data-testid="student-name-input"
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium text-slate-700">Email</label>
                        <Input
                          type="email"
                          value={newStudent.email}
                          onChange={(e) => setNewStudent({ ...newStudent, email: e.target.value })}
                          placeholder="student@college.edu"
                          required
                          data-testid="student-email-input"
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium text-slate-700">College</label>
                        <Input
                          value={newStudent.college}
                          onChange={(e) => setNewStudent({ ...newStudent, college: e.target.value })}
                          placeholder="Law College Name"
                          required
                          data-testid="student-college-input"
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium text-slate-700">Skills (comma-separated)</label>
                        <Input
                          value={newStudent.skills}
                          onChange={(e) => setNewStudent({ ...newStudent, skills: e.target.value })}
                          placeholder="Criminal Law, RTI, Drafting"
                          data-testid="student-skills-input"
                        />
                      </div>
                      <Button type="submit" className="w-full bg-orange-500 hover:bg-orange-600" data-testid="submit-student-btn">
                        Add Student
                      </Button>
                    </form>
                  </DialogContent>
                </Dialog>
              </CardHeader>
              <CardContent className="p-0">
                {students.length === 0 ? (
                  <div className="p-8 text-center text-slate-500">
                    <GraduationCap className="w-12 h-12 mx-auto mb-4 text-slate-300" />
                    <p>No students registered yet. Add a student or load sample data.</p>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {students.map((student) => (
                      <div key={student.id} className="p-4 hover:bg-slate-50 transition-colors" data-testid={`student-${student.id}`}>
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <h4 className="font-semibold text-slate-900">{student.name}</h4>
                            <div className="flex items-center gap-4 mt-1 text-sm text-slate-500">
                              <span className="flex items-center gap-1">
                                <Mail className="w-3 h-3" />
                                {student.email}
                              </span>
                              <span className="flex items-center gap-1">
                                <Building className="w-3 h-3" />
                                {student.college}
                              </span>
                            </div>
                            <div className="flex flex-wrap gap-1 mt-2">
                              {student.skills?.map((skill, i) => (
                                <Badge key={i} variant="secondary" className="text-xs">
                                  {skill}
                                </Badge>
                              ))}
                            </div>
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-slate-400 hover:text-red-500"
                            onClick={() => handleDeleteStudent(student.id)}
                            data-testid={`delete-student-${student.id}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Cases Tab */}
          <TabsContent value="cases">
            <Card className="bg-white border-slate-200">
              <CardHeader className="border-b border-slate-100 flex flex-row items-center justify-between">
                <CardTitle className="font-heading">Legal Cases</CardTitle>
                <Dialog open={caseDialogOpen} onOpenChange={setCaseDialogOpen}>
                  <DialogTrigger asChild>
                    <Button className="bg-slate-900 hover:bg-slate-800" data-testid="add-case-btn">
                      <Plus className="w-4 h-4 mr-2" />
                      Add Case
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle className="font-heading">Add New Case</DialogTitle>
                    </DialogHeader>
                    <form onSubmit={handleAddCase} className="space-y-4 mt-4">
                      <div>
                        <label className="text-sm font-medium text-slate-700">Title</label>
                        <Input
                          value={newCase.title}
                          onChange={(e) => setNewCase({ ...newCase, title: e.target.value })}
                          placeholder="Case Title"
                          required
                          data-testid="case-title-input"
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium text-slate-700">Description</label>
                        <Textarea
                          value={newCase.description}
                          onChange={(e) => setNewCase({ ...newCase, description: e.target.value })}
                          placeholder="Describe the case..."
                          required
                          data-testid="case-desc-input"
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium text-slate-700">Category</label>
                        <Select
                          value={newCase.category}
                          onValueChange={(v) => setNewCase({ ...newCase, category: v })}
                        >
                          <SelectTrigger data-testid="case-category-select">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="fir">FIR / Police</SelectItem>
                            <SelectItem value="rti">RTI</SelectItem>
                            <SelectItem value="consumer">Consumer</SelectItem>
                            <SelectItem value="labour">Labour</SelectItem>
                            <SelectItem value="family">Family</SelectItem>
                            <SelectItem value="property">Property</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <Button type="submit" className="w-full bg-orange-500 hover:bg-orange-600" data-testid="submit-case-btn">
                        Add Case
                      </Button>
                    </form>
                  </DialogContent>
                </Dialog>
              </CardHeader>
              <CardContent className="p-0">
                {cases.length === 0 ? (
                  <div className="p-8 text-center text-slate-500">
                    <Briefcase className="w-12 h-12 mx-auto mb-4 text-slate-300" />
                    <p>No cases available. Add a case or load sample data.</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Title</th>
                          <th>Category</th>
                          <th>Status</th>
                          <th>Assigned To</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {cases.map((caseItem) => (
                          <tr key={caseItem.id} data-testid={`case-${caseItem.id}`}>
                            <td>
                              <div>
                                <p className="font-medium text-slate-900">{caseItem.title}</p>
                                <p className="text-sm text-slate-500 truncate max-w-xs">{caseItem.description}</p>
                              </div>
                            </td>
                            <td>
                              <Badge variant="outline">{getCategoryLabel(caseItem.category)}</Badge>
                            </td>
                            <td>
                              <Badge className={getStatusStyle(caseItem.status)}>
                                {caseItem.status}
                              </Badge>
                            </td>
                            <td>
                              {caseItem.status === 'open' ? (
                                <Select onValueChange={(v) => handleAssignCase(caseItem.id, v)}>
                                  <SelectTrigger className="w-[180px]" data-testid={`assign-case-${caseItem.id}`}>
                                    <SelectValue placeholder="Assign to..." />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {students.map((s) => (
                                      <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              ) : (
                                <span className="text-sm text-slate-600">
                                  {students.find(s => s.id === caseItem.assigned_student_id)?.name || '-'}
                                </span>
                              )}
                            </td>
                            <td>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="text-slate-400 hover:text-red-500"
                                onClick={() => handleDeleteCase(caseItem.id)}
                                data-testid={`delete-case-${caseItem.id}`}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
