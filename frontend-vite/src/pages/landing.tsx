import { Link } from "react-router-dom";
import {
  Zap, ArrowRight, CheckCircle, MessageSquare, Image, Bot,
  BarChart3, Shield, Globe, Star, ChevronDown, Play,
  Sparkles, Layout, Brain, Users, Clock, Phone,
} from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

// ─── Pricing ────────────────────────────────────────

const plans = [
  {
    name: "Starter",
    price: "9 900",
    period: "/ mois",
    description: "Pour les entrepreneurs qui debutent",
    features: [
      "1 marque",
      "3 comptes sociaux",
      "20 posts IA / mois",
      "50 generations IA",
      "Support WhatsApp basique",
      "5 documents KB",
    ],
    cta: "Commencer gratuitement",
    popular: false,
  },
  {
    name: "Pro",
    price: "29 900",
    period: "/ mois",
    description: "Pour les entreprises en croissance",
    features: [
      "3 marques",
      "10 comptes sociaux",
      "100 posts IA / mois",
      "500 generations IA",
      "Support WhatsApp + Messenger",
      "50 documents KB",
      "Agent Affichiste IA",
      "Calendrier editorial IA",
      "Analytics avances",
    ],
    cta: "Essai gratuit 14 jours",
    popular: true,
  },
  {
    name: "Business",
    price: "79 900",
    period: "/ mois",
    description: "Pour les agences et grandes entreprises",
    features: [
      "Marques illimitees",
      "Comptes sociaux illimites",
      "Posts illimites",
      "Generations IA illimitees",
      "Tous les canaux",
      "Documents KB illimites",
      "15 agents IA specialises",
      "Design DNA & templates",
      "API access",
      "Support prioritaire",
    ],
    cta: "Contacter les ventes",
    popular: false,
  },
];

// ─── Features ───────────────────────────────────────

const features = [
  {
    icon: Sparkles,
    title: "Contenu IA personnalise",
    description: "L'IA redige vos posts en s'adaptant au ton de votre marque, a votre audience et a chaque reseau social.",
    color: "from-brand-400 to-brand-600",
    bgLight: "bg-brand-50",
  },
  {
    icon: Layout,
    title: "Affiches marketing pro",
    description: "Generez des visuels marketing avec titre, CTA et couleurs de marque. L'IA apprend votre style visuel.",
    color: "from-purple-400 to-purple-600",
    bgLight: "bg-purple-50",
  },
  {
    icon: MessageSquare,
    title: "Support client 24h/24",
    description: "Repondez automatiquement sur WhatsApp et Messenger. L'IA utilise votre base de connaissances.",
    color: "from-emerald-400 to-emerald-600",
    bgLight: "bg-emerald-50",
  },
  {
    icon: Brain,
    title: "15 agents IA specialises",
    description: "Copywriter, graphiste, vendeur, stratege, analyste... Chaque aspect de votre marketing est automatise.",
    color: "from-amber-400 to-amber-600",
    bgLight: "bg-amber-50",
  },
  {
    icon: BarChart3,
    title: "Analytics & strategie",
    description: "Rapports automatiques, recommandations, meilleurs horaires de publication par pays africain.",
    color: "from-sky-400 to-sky-600",
    bgLight: "bg-sky-50",
  },
  {
    icon: Shield,
    title: "Securise & multi-tenant",
    description: "Chiffrement AES-256, isolation des donnees, RBAC 6 roles, moderation automatique du contenu.",
    color: "from-rose-400 to-rose-600",
    bgLight: "bg-rose-50",
  },
];

// ─── Steps ──────────────────────────────────────────

const steps = [
  { num: "01", title: "Creez votre marque", desc: "Definissez votre identite, ton, couleurs et produits en 2 minutes.", icon: Globe },
  { num: "02", title: "Connectez vos reseaux", desc: "Facebook, Instagram, WhatsApp, TikTok — OAuth en un clic.", icon: Phone },
  { num: "03", title: "L'IA prend le relais", desc: "Generation de contenu, publication, support client — tout est automatise.", icon: Bot },
];

// ─── FAQ ────────────────────────────────────────────

const faqs = [
  { q: "Est-ce que ca marche avec WhatsApp ?", a: "Oui ! OptimusAI se connecte a WhatsApp Business API pour repondre automatiquement a vos clients avec votre base de connaissances. Les reponses dans les 24h sont gratuites." },
  { q: "L'IA ecrit vraiment en francais correct ?", a: "Oui, nos agents sont specialement entraines pour le francais d'Afrique de l'Ouest. Ils comprennent les expressions locales et adaptent le ton a chaque plateforme." },
  { q: "Combien coute la generation d'images ?", a: "Les images sont generees localement avec FLUX AI — pas de cout par image. C'est inclus dans votre forfait." },
  { q: "Je peux payer avec Orange Money ?", a: "Oui ! Nous acceptons Orange Money, Moov Money, Wave, et les cartes bancaires via nos partenaires de paiement locaux." },
  { q: "Mes donnees sont-elles en securite ?", a: "Absolument. Chiffrement AES-256 pour les tokens, isolation des donnees par entreprise, et moderation automatique de tout le contenu." },
  { q: "Puis-je essayer gratuitement ?", a: "Oui, le plan Starter offre 14 jours d'essai gratuit. Pas de carte bancaire requise." },
];

// ─── Component ──────────────────────────────────────

export default function LandingPage() {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  return (
    <div className="min-h-screen bg-white">
      {/* ━━━ Navbar ━━━ */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-lg border-b border-gray-100">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-6 h-16">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-600 shadow-md shadow-brand-500/20">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <span className="text-lg font-bold text-gray-900 tracking-tight">OptimusAI</span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">Fonctionnalites</a>
            <a href="#pricing" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">Tarifs</a>
            <a href="#faq" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">FAQ</a>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/auth" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">Connexion</Link>
            <Link to="/auth" className="inline-flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-600 transition-all active:scale-[0.98]">
              Commencer <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </nav>

      {/* ━━━ Hero ━━━ */}
      <section className="relative pt-32 pb-20 px-6 overflow-hidden">
        {/* Background decoration */}
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-20 left-10 w-72 h-72 bg-brand-100 rounded-full blur-3xl opacity-40" />
          <div className="absolute bottom-10 right-10 w-96 h-96 bg-sky-100 rounded-full blur-3xl opacity-30" />
        </div>

        <div className="max-w-6xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 rounded-full bg-brand-50 px-4 py-1.5 text-xs font-semibold text-brand-700 mb-6">
            <Sparkles className="h-3.5 w-3.5" /> 15 agents IA specialises pour votre business
          </div>

          <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold text-gray-900 tracking-tight leading-[1.1]">
            Votre equipe marketing
            <br />
            <span className="bg-gradient-to-r from-brand-500 to-sky-500 bg-clip-text text-transparent">
              100% IA
            </span>
          </h1>

          <p className="mt-6 text-lg md:text-xl text-gray-500 max-w-2xl mx-auto leading-relaxed">
            Generez du contenu, creez des affiches, repondez a vos clients sur WhatsApp
            et publiez sur tous vos reseaux — automatiquement.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/auth"
              className="inline-flex items-center gap-2 rounded-2xl bg-brand-500 px-8 py-4 text-base font-bold text-white shadow-lg shadow-brand-500/25 hover:bg-brand-600 hover:shadow-xl transition-all active:scale-[0.98]"
            >
              Essai gratuit 14 jours <ArrowRight className="h-5 w-5" />
            </Link>
            <a
              href="#features"
              className="inline-flex items-center gap-2 rounded-2xl border border-gray-200 bg-white px-8 py-4 text-base font-semibold text-gray-700 hover:border-gray-300 hover:bg-gray-50 transition-all"
            >
              <Play className="h-4 w-4" /> Voir comment ca marche
            </a>
          </div>

          <p className="mt-4 text-xs text-gray-400">Pas de carte bancaire requise · Annulation a tout moment</p>

          {/* Stats */}
          <div className="mt-16 flex items-center justify-center gap-8 md:gap-16">
            {[
              { value: "15", label: "Agents IA" },
              { value: "5", label: "Reseaux sociaux" },
              { value: "24/7", label: "Support auto" },
              { value: "<2min", label: "Pour un post" },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <p className="text-2xl md:text-3xl font-bold text-gray-900">{s.value}</p>
                <p className="text-xs text-gray-500 mt-1">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ━━━ Logos ━━━ */}
      <section className="py-12 border-y border-gray-100 bg-gray-50/50">
        <div className="max-w-6xl mx-auto px-6">
          <p className="text-center text-xs font-semibold text-gray-400 uppercase tracking-wider mb-6">
            Concu pour les entreprises africaines
          </p>
          <div className="flex items-center justify-center gap-8 md:gap-16 opacity-40">
            {["Burkina Faso", "Cote d'Ivoire", "Senegal", "Mali", "Cameroun"].map((c) => (
              <div key={c} className="flex items-center gap-2">
                <Globe className="h-5 w-5" />
                <span className="text-sm font-semibold text-gray-600 hidden sm:block">{c}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ━━━ Features ━━━ */}
      <section id="features" className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold text-brand-600 mb-2">Fonctionnalites</p>
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900">
              Tout ce qu'un community manager fait.
              <br />
              <span className="text-gray-400">Mais en automatique.</span>
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f) => (
              <div key={f.title} className="group rounded-2xl border border-gray-100 p-6 hover:border-gray-200 hover:shadow-lg transition-all duration-300">
                <div className={cn("inline-flex rounded-xl p-3 mb-4", f.bgLight)}>
                  <f.icon className="h-6 w-6 text-gray-700" />
                </div>
                <h3 className="text-lg font-bold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ━━━ How it works ━━━ */}
      <section className="py-24 px-6 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold text-brand-600 mb-2">Comment ca marche</p>
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900">Operationnel en 3 etapes</h2>
          </div>

          <div className="space-y-8">
            {steps.map((s, i) => (
              <div key={s.num} className="flex items-start gap-6 group">
                <div className="flex flex-col items-center">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-500 text-white font-bold text-lg shadow-lg shadow-brand-500/20 group-hover:scale-110 transition-transform">
                    {s.num}
                  </div>
                  {i < steps.length - 1 && <div className="w-0.5 h-12 bg-brand-200 mt-2" />}
                </div>
                <div className="pt-2">
                  <h3 className="text-xl font-bold text-gray-900 mb-1">{s.title}</h3>
                  <p className="text-gray-500">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ━━━ Pricing ━━━ */}
      <section id="pricing" className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold text-brand-600 mb-2">Tarifs</p>
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900">Simple et transparent</h2>
            <p className="mt-3 text-gray-500">Prix en FCFA · Paiement Orange Money, Wave, carte bancaire</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={cn(
                  "rounded-2xl border p-8 relative",
                  plan.popular
                    ? "border-brand-500 shadow-xl shadow-brand-500/10 scale-105"
                    : "border-gray-200",
                )}
              >
                {plan.popular && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 rounded-full bg-brand-500 px-4 py-1 text-xs font-bold text-white">
                    Plus populaire
                  </div>
                )}
                <h3 className="text-xl font-bold text-gray-900">{plan.name}</h3>
                <p className="text-sm text-gray-500 mt-1">{plan.description}</p>
                <div className="mt-6 flex items-baseline gap-1">
                  <span className="text-4xl font-bold text-gray-900">{plan.price}</span>
                  <span className="text-sm text-gray-400">FCFA {plan.period}</span>
                </div>
                <Link
                  to="/auth"
                  className={cn(
                    "mt-6 block w-full rounded-xl py-3 text-center text-sm font-bold transition-all",
                    plan.popular
                      ? "bg-brand-500 text-white shadow-sm hover:bg-brand-600"
                      : "border border-gray-200 text-gray-700 hover:bg-gray-50",
                  )}
                >
                  {plan.cta}
                </Link>
                <ul className="mt-6 space-y-3">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-sm text-gray-600">
                      <CheckCircle className="h-4 w-4 text-brand-500 shrink-0 mt-0.5" /> {f}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ━━━ Testimonials ━━━ */}
      <section className="py-24 px-6 bg-gray-50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold text-brand-600 mb-2">Temoignages</p>
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900">Ils automatisent leur marketing</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { name: "Aminata K.", role: "Fondatrice, Wax Elegance", city: "Ouagadougou", text: "OptimusAI a transforme notre presence sur les reseaux. On genere 10x plus de contenu qu'avant, et nos clients WhatsApp recoivent des reponses en 30 secondes." },
              { name: "Ibrahim D.", role: "Gerant, Saveur du Sahel", city: "Abidjan", text: "Le support client automatique sur WhatsApp nous a permis de servir 3x plus de clients sans embaucher. L'IA connait notre menu mieux que nous !" },
              { name: "Fatou S.", role: "Directrice Marketing, TechBF", city: "Dakar", text: "Les affiches generees sont bluffantes. On a arrete notre abonnement Canva. L'IA a appris notre style en uploadant 5 references." },
            ].map((t) => (
              <div key={t.name} className="rounded-2xl bg-white border border-gray-100 p-6 shadow-sm">
                <div className="flex gap-1 mb-4">
                  {[1, 2, 3, 4, 5].map((i) => <Star key={i} className="h-4 w-4 fill-amber-400 text-amber-400" />)}
                </div>
                <p className="text-sm text-gray-600 leading-relaxed mb-6">"{t.text}"</p>
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-100 text-brand-700 font-bold text-sm">
                    {t.name.split(" ").map(w => w[0]).join("")}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{t.name}</p>
                    <p className="text-xs text-gray-400">{t.role} · {t.city}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ━━━ FAQ ━━━ */}
      <section id="faq" className="py-24 px-6">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold text-brand-600 mb-2">FAQ</p>
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900">Questions frequentes</h2>
          </div>
          <div className="space-y-3">
            {faqs.map((faq, i) => (
              <div key={i} className="rounded-2xl border border-gray-100 overflow-hidden">
                <button
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="flex items-center justify-between w-full px-6 py-4 text-left hover:bg-gray-50 transition-colors"
                >
                  <span className="text-sm font-semibold text-gray-900">{faq.q}</span>
                  <ChevronDown className={cn("h-4 w-4 text-gray-400 transition-transform", openFaq === i && "rotate-180")} />
                </button>
                {openFaq === i && (
                  <div className="px-6 pb-4">
                    <p className="text-sm text-gray-500 leading-relaxed">{faq.a}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ━━━ Final CTA ━━━ */}
      <section className="py-24 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="rounded-3xl bg-gradient-to-br from-gray-900 via-gray-900 to-brand-900 p-12 md:p-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Pret a automatiser votre marketing ?
            </h2>
            <p className="text-gray-400 mb-8 max-w-xl mx-auto">
              Rejoignez les entreprises africaines qui laissent l'IA gerer leur contenu,
              leur support client et leur strategie sociale.
            </p>
            <Link
              to="/auth"
              className="inline-flex items-center gap-2 rounded-2xl bg-brand-500 px-8 py-4 text-base font-bold text-white shadow-lg shadow-brand-500/25 hover:bg-brand-600 transition-all active:scale-[0.98]"
            >
              Commencer gratuitement <ArrowRight className="h-5 w-5" />
            </Link>
          </div>
        </div>
      </section>

      {/* ━━━ Footer ━━━ */}
      <footer className="border-t border-gray-100 py-12 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div className="col-span-2 md:col-span-1">
              <div className="flex items-center gap-2 mb-4">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500">
                  <Zap className="h-4 w-4 text-white" />
                </div>
                <span className="font-bold text-gray-900">OptimusAI</span>
              </div>
              <p className="text-xs text-gray-400 leading-relaxed">
                Plateforme de marketing automation et support client IA pour les entreprises africaines.
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-900 uppercase tracking-wider mb-3">Produit</p>
              <div className="space-y-2">
                <a href="#features" className="block text-sm text-gray-500 hover:text-gray-700">Fonctionnalites</a>
                <a href="#pricing" className="block text-sm text-gray-500 hover:text-gray-700">Tarifs</a>
                <a href="#faq" className="block text-sm text-gray-500 hover:text-gray-700">FAQ</a>
              </div>
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-900 uppercase tracking-wider mb-3">Legal</p>
              <div className="space-y-2">
                <Link to="/terms" className="block text-sm text-gray-500 hover:text-gray-700">Conditions</Link>
                <Link to="/privacy" className="block text-sm text-gray-500 hover:text-gray-700">Confidentialite</Link>
              </div>
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-900 uppercase tracking-wider mb-3">Contact</p>
              <div className="space-y-2">
                <p className="text-sm text-gray-500">contact@optimusai.app</p>
                <p className="text-sm text-gray-500">Ouagadougou, Burkina Faso</p>
              </div>
            </div>
          </div>
          <div className="mt-12 pt-6 border-t border-gray-100 text-center">
            <p className="text-xs text-gray-400">2026 OptimusAI. Tous droits reserves. Concu avec passion au Burkina Faso.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
