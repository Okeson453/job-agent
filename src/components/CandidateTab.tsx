import React, { useState } from 'react';
import {
  User,
  Mail,
  Phone,
  MapPin,
  DollarSign,
  Clock,
  Shield,
  Layers,
  Code2,
  FileQuestion,
  Search,
  Plus,
  Save,
  CheckCircle2,
  Briefcase,
} from 'lucide-react';
import { AnswerBankItem, CandidateProfile, CandidateProject, CandidateSkill } from '../types';

interface CandidateTabProps {
  profile: CandidateProfile;
  projects: CandidateProject[];
  skills: CandidateSkill[];
  answers: AnswerBankItem[];
  onUpdateProfile: (updates: Partial<CandidateProfile>) => void;
  onAddAnswer: (category: string, question: string, answer: string) => void;
}

export const CandidateTab: React.FC<CandidateTabProps> = ({
  profile,
  projects,
  skills,
  answers,
  onUpdateProfile,
  onAddAnswer,
}) => {
  const [activeSubTab, setActiveSubTab] = useState<'profile' | 'projects' | 'skills' | 'answers'>('profile');
  const [answerSearch, setAnswerSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');

  // New QA modal state
  const [showAddQa, setShowAddQa] = useState(false);
  const [newCategory, setNewCategory] = useState('behavioral');
  const [newQuestion, setNewQuestion] = useState('');
  const [newAnswer, setNewAnswer] = useState('');

  // Editable profile state
  const [isEditing, setIsEditing] = useState(false);
  const [editFullName, setEditFullName] = useState(profile.full_name);
  const [editEmail, setEditEmail] = useState(profile.email);
  const [editPhone, setEditPhone] = useState(profile.phone);
  const [editLocation, setEditLocation] = useState(profile.location);
  const [editMinSalary, setEditMinSalary] = useState(String(profile.min_salary || 65000));
  const [editSummary, setEditSummary] = useState(profile.summary);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    onUpdateProfile({
      full_name: editFullName,
      email: editEmail,
      phone: editPhone,
      location: editLocation,
      min_salary: Number(editMinSalary) || null,
      summary: editSummary,
    });
    setIsEditing(false);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  const handleCreateAnswer = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newQuestion.trim() || !newAnswer.trim()) return;
    onAddAnswer(newCategory, newQuestion.trim(), newAnswer.trim());
    setNewQuestion('');
    setNewAnswer('');
    setShowAddQa(false);
  };

  const categories = ['ALL', ...Array.from(new Set(answers.map((a) => a.category)))];

  const filteredAnswers = answers.filter((a) => {
    if (selectedCategory !== 'ALL' && a.category !== selectedCategory) return false;
    if (
      answerSearch &&
      !a.question.toLowerCase().includes(answerSearch.toLowerCase()) &&
      !a.answer.toLowerCase().includes(answerSearch.toLowerCase())
    )
      return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Profile Overview Card */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
          <div className="flex items-start space-x-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-cyan-500 p-0.5 shadow-lg shadow-blue-500/20 shrink-0">
              <div className="w-full h-full bg-slate-950 rounded-[14px] flex items-center justify-center">
                <User className="w-7 h-7 text-blue-400" />
              </div>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-extrabold text-white">{profile.full_name}</h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">
                  VERIFIED CANDIDATE
                </span>
              </div>
              <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">{profile.summary}</p>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 pt-2 text-xs text-slate-300 font-mono">
                <span className="flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-blue-400" />
                  <span>{profile.email}</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <Phone className="w-3.5 h-3.5 text-cyan-400" />
                  <span>{profile.phone}</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                  <span>{profile.location}</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <DollarSign className="w-3.5 h-3.5 text-amber-400" />
                  <span>
                    Min: ${profile.min_salary?.toLocaleString()} {profile.currency}
                  </span>
                </span>
              </div>
            </div>
          </div>

          <button
            onClick={() => setIsEditing(!isEditing)}
            className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl text-xs font-semibold self-start transition-all cursor-pointer"
          >
            {isEditing ? 'Cancel Edit' : 'Edit Profile'}
          </button>
        </div>

        {savedSuccess && (
          <div className="mt-4 p-2.5 bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs rounded-xl flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            <span>Candidate profile updated and persisted.</span>
          </div>
        )}

        {/* Profile Edit Form */}
        {isEditing && (
          <form onSubmit={handleSaveProfile} className="mt-6 pt-6 border-t border-slate-800 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
              <div>
                <label className="block text-slate-400 font-semibold mb-1">Full Legal Name</label>
                <input
                  type="text"
                  value={editFullName}
                  onChange={(e) => setEditFullName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white font-mono"
                  required
                />
              </div>
              <div>
                <label className="block text-slate-400 font-semibold mb-1">Email</label>
                <input
                  type="email"
                  value={editEmail}
                  onChange={(e) => setEditEmail(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white font-mono"
                  required
                />
              </div>
              <div>
                <label className="block text-slate-400 font-semibold mb-1">Phone</label>
                <input
                  type="text"
                  value={editPhone}
                  onChange={(e) => setEditPhone(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white font-mono"
                />
              </div>
              <div>
                <label className="block text-slate-400 font-semibold mb-1">Min Salary (USD)</label>
                <input
                  type="number"
                  value={editMinSalary}
                  onChange={(e) => setEditMinSalary(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white font-mono"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs text-slate-400 font-semibold mb-1">Professional Summary</label>
              <textarea
                rows={3}
                value={editSummary}
                onChange={(e) => setEditSummary(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-white font-mono"
              />
            </div>

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="px-3 py-1.5 bg-slate-800 text-slate-400 rounded-lg text-xs"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Save Updates</span>
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Sub Tabs: Projects, Skills, Answer Bank */}
      <div className="flex items-center space-x-2 border-b border-slate-800 pb-2 text-xs font-semibold">
        <button
          onClick={() => setActiveSubTab('profile')}
          className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
            activeSubTab === 'profile' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
          }`}
        >
          Target Preferences & Roles
        </button>
        <button
          onClick={() => setActiveSubTab('projects')}
          className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
            activeSubTab === 'projects' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
          }`}
        >
          Candidate Projects ({projects.length})
        </button>
        <button
          onClick={() => setActiveSubTab('skills')}
          className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
            activeSubTab === 'skills' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
          }`}
        >
          Verified Skills ({skills.length})
        </button>
        <button
          onClick={() => setActiveSubTab('answers')}
          className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
            activeSubTab === 'answers' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
          }`}
        >
          Answer Bank QA ({answers.length})
        </button>
      </div>

      {/* Sub Tab: Target Preferences */}
      {activeSubTab === 'profile' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-blue-400" />
              <span>Target Role Families</span>
            </h3>
            <div className="space-y-1.5 text-xs font-mono">
              {profile.preferred_roles.map((role) => (
                <div key={role} className="p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-300">
                  {role}
                </div>
              ))}
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-emerald-400" />
              <span>Availability & Work Status</span>
            </h3>
            <div className="space-y-2 text-xs">
              <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg">
                <span className="text-slate-500 font-mono block text-[10px]">NOTICE PERIOD</span>
                <span className="font-semibold text-slate-200">{profile.availability}</span>
              </div>
              <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg">
                <span className="text-slate-500 font-mono block text-[10px]">WORK AUTHORIZATION</span>
                <span className="text-slate-200 leading-relaxed">{profile.work_authorization}</span>
              </div>
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Shield className="w-4 h-4 text-purple-400" />
              <span>Tailored CV Profiles</span>
            </h3>
            <div className="space-y-2 text-xs font-mono">
              {['backend.pdf', 'security.pdf', 'fullstack.pdf', 'trading.pdf', 'general.pdf'].map((cv) => (
                <div
                  key={cv}
                  className="flex items-center justify-between p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-300"
                >
                  <span className="font-semibold text-blue-400">{cv}</span>
                  <span className="text-[10px] text-emerald-400">SEEDED</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Sub Tab: Projects */}
      {activeSubTab === 'projects' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {projects.map((proj) => (
            <div
              key={proj.id}
              className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h4 className="text-base font-bold text-white">{proj.name}</h4>
                  <p className="text-xs text-slate-400 mt-0.5">{proj.description}</p>
                </div>
                <span
                  className={`px-2.5 py-0.5 rounded text-[10px] font-mono uppercase font-bold shrink-0 ${
                    proj.implementation_status === 'implemented'
                      ? 'bg-blue-950 text-blue-300 border border-blue-800'
                      : proj.implementation_status === 'designed'
                      ? 'bg-amber-950 text-amber-300 border border-amber-800'
                      : 'bg-purple-950 text-purple-300 border border-purple-800'
                  }`}
                >
                  Status: {proj.implementation_status}
                </span>
              </div>

              <div className="text-xs space-y-1.5 font-mono text-slate-300">
                <div className="text-[11px] text-slate-400 bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-slate-500 font-semibold block text-[10px]">PRODUCTION CLAIM:</span>
                  <span className="text-amber-400 font-semibold">{proj.production_deployment}</span>
                </div>
                <div className="text-[11px] text-slate-400 bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-slate-500 font-semibold block text-[10px]">DESIGN / EVIDENCE:</span>
                  <span>{proj.design_experience}</span>
                </div>
              </div>

              <div className="flex flex-wrap gap-1.5 pt-1">
                {proj.verified_technologies.map((tech) => (
                  <span
                    key={tech}
                    className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-950 text-slate-300 border border-slate-800"
                  >
                    {tech}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Sub Tab: Skills */}
      {activeSubTab === 'skills' && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {skills.map((skill) => (
              <div
                key={skill.id}
                className="bg-slate-950 border border-slate-800 rounded-xl p-3 flex items-center justify-between text-xs"
              >
                <div>
                  <div className="font-bold text-slate-200">{skill.name}</div>
                  <div className="text-[10px] text-slate-500 font-mono">{skill.category}</div>
                </div>
                <div className="text-right">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-900 text-blue-400 border border-slate-800">
                    {skill.proficiency}
                  </span>
                  <div className="text-[9px] text-slate-500 font-mono mt-0.5 uppercase">
                    tier: {skill.evidence_level}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sub Tab: Answer Bank */}
      {activeSubTab === 'answers' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
            <div className="relative w-full sm:w-80">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
              <input
                type="text"
                value={answerSearch}
                onChange={(e) => setAnswerSearch(e.target.value)}
                placeholder="Search QA bank..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white font-mono"
              >
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {c.toUpperCase()}
                  </option>
                ))}
              </select>

              <button
                onClick={() => setShowAddQa(true)}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1 cursor-pointer shrink-0"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add QA</span>
              </button>
            </div>
          </div>

          <div className="space-y-3">
            {filteredAnswers.map((item) => (
              <div
                key={item.id}
                className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 text-xs space-y-1.5 shadow-sm"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-blue-400 font-mono uppercase text-[10px] bg-blue-950 px-2 py-0.5 rounded border border-blue-900">
                    {item.category}
                  </span>
                  <span className="text-slate-500 font-mono text-[10px]">{item.id}</span>
                </div>
                <div className="font-bold text-slate-200">Q: {item.question}</div>
                <div className="text-slate-400 leading-relaxed pl-2 border-l-2 border-slate-700">
                  {item.answer}
                </div>
              </div>
            ))}
          </div>

          {/* Add QA Modal */}
          {showAddQa && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-xl">
                <h3 className="text-base font-bold text-white">Add Answer Bank Item</h3>
                <form onSubmit={handleCreateAnswer} className="space-y-3 text-xs">
                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">Category</label>
                    <select
                      value={newCategory}
                      onChange={(e) => setNewCategory(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white font-mono"
                    >
                      <option value="behavioral">Behavioral / STAR</option>
                      <option value="technical">Technical</option>
                      <option value="availability">Availability</option>
                      <option value="compensation">Compensation</option>
                      <option value="work_authorization">Work Authorization</option>
                      <option value="career">Career Goals</option>
                      <option value="custom">Custom</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">Question Prompt</label>
                    <input
                      type="text"
                      value={newQuestion}
                      onChange={(e) => setNewQuestion(e.target.value)}
                      placeholder="e.g. Tell us about a time you resolved a difficult bug..."
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">
                      Evidence-Grounded Answer
                    </label>
                    <textarea
                      rows={4}
                      value={newAnswer}
                      onChange={(e) => setNewAnswer(e.target.value)}
                      placeholder="Answer referencing verified candidate experience..."
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white"
                      required
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowAddQa(false)}
                      className="px-3 py-1.5 bg-slate-800 text-slate-400 rounded-lg"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-semibold"
                    >
                      Save to Bank
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
