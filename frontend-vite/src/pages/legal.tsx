import { useLocation } from "react-router-dom";
import { Zap } from "lucide-react";

export default function LegalPage() {
  const { pathname } = useLocation();
  const isTerms = pathname.includes("terms");

  return (
    <div className="min-h-screen bg-page">
      <div className="max-w-3xl mx-auto px-6 py-16">
        <div className="flex items-center gap-3 mb-8">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500">
            <Zap className="h-5 w-5 text-white" />
          </div>
          <span className="text-xl font-bold text-gray-900">OptimusAI</span>
        </div>

        {isTerms ? (
          <>
            <h1 className="text-3xl font-bold text-gray-900 mb-6">Conditions Generales d'Utilisation</h1>
            <div className="prose prose-gray max-w-none space-y-4 text-sm text-gray-600">
              <p><strong>Derniere mise a jour :</strong> Mars 2026</p>
              <h2 className="text-lg font-semibold text-gray-800 mt-6">1. Acceptation des conditions</h2>
              <p>En utilisant OptimusAI, vous acceptez les presentes conditions generales d'utilisation. OptimusAI est une plateforme SaaS de marketing automation et de support client propulsee par l'intelligence artificielle, destinee aux entreprises africaines.</p>
              <h2 className="text-lg font-semibold text-gray-800 mt-6">2. Description du service</h2>
              <p>OptimusAI fournit des outils de generation de contenu marketing, de gestion des reseaux sociaux (Facebook, Instagram, TikTok, WhatsApp), de support client automatise, et d'analyse de performance. Le service utilise des modeles d'IA pour assister la creation de contenu.</p>
              <h2 className="text-lg font-semibold text-gray-800 mt-6">3. Comptes utilisateurs</h2>
              <p>Vous etes responsable de maintenir la confidentialite de vos identifiants de connexion. Chaque compte est lie a un tenant (entreprise) et les donnees sont isolees entre tenants.</p>
              <h2 className="text-lg font-semibold text-gray-800 mt-6">4. Utilisation acceptable</h2>
              <p>Vous vous engagez a ne pas utiliser le service pour generer du contenu illegal, haineux, trompeur ou portant atteinte aux droits d'autrui. Le contenu genere par l'IA doit etre verifie avant publication.</p>
              <h2 className="text-lg font-semibold text-gray-800 mt-6">5. Propriete intellectuelle</h2>
              <p>Le contenu genere via OptimusAI vous appartient. OptimusAI conserve les droits sur sa plateforme, son code et ses modeles.</p>
              <h2 className="text-lg font-semibold text-gray-800 mt-6">6. Integrations tierces</h2>
              <p>OptimusAI se connecte a des plateformes tierces (Meta, TikTok, etc.) via leurs APIs officielles. L'utilisation de ces plateformes est soumise a leurs propres conditions.</p>
              <h2 className="text-lg font-semibold text-gray-800 mt-6">7. Limitation de responsabilite</h2>
              <p>OptimusAI est fourni "en l'etat". Nous ne garantissons pas que le contenu genere par l'IA sera exempt d'erreurs. L'utilisateur est responsable de la verification et de la publication du contenu.</p>
              <h2 className="text-lg font-semibold text-gray-800 mt-6">8. Contact</h2>
              <p>Pour toute question, contactez-nous a : contact@optimusai.app</p>
            </div>
          </>
        ) : (
          <>
            <h1 className="text-3xl font-bold text-gray-900 mb-6">Politique de Confidentialite</h1>
            <div className="prose prose-gray max-w-none space-y-4 text-sm text-gray-600">
              <p><strong>Derniere mise a jour :</strong> Mars 2026</p>
              <h2 className="text-lg font-semibold text-gray-800 mt-6">1. Donnees collectees</h2>
              <p>OptimusAI collecte les donnees suivantes : informations de compte (nom, email, entreprise), contenu cree sur la plateforme, donnees de connexion aux reseaux sociaux (tokens chiffres), et donnees d'utilisation du service.</p>
              <h2 className="text-lg font-semibold text-gray-800 mt-6">2. Utilisation des donnees</h2>
              <p>Vos donnees sont utilisees pour : fournir le service (generation de contenu, publication, support client), ameliorer nos modeles d'IA, et vous envoyer des notifications liees au service.</p>
              <h2 className="text-lg font-semibold text-gray-800 mt-6">3. Stockage et securite</h2>
              <p>Les donnees sont stockees de maniere securisee. Les tokens d'acces aux reseaux sociaux sont chiffres (AES-256). Les mots de passe sont hashes (bcrypt). L'acces aux donnees est isole par tenant.</p>
              <h2 className="text-lg font-semibold text-gray-800 mt-6">4. Partage des donnees</h2>
              <p>Nous ne vendons pas vos donnees. Vos donnees sont partagees uniquement avec les plateformes que vous connectez (Meta, TikTok) dans le cadre des fonctionnalites que vous utilisez.</p>
              <h2 className="text-lg font-semibold text-gray-800 mt-6">5. Donnees des reseaux sociaux</h2>
              <p>Lorsque vous connectez votre compte TikTok, Facebook ou Instagram, nous accedons aux donnees autorisees (profil, statistiques, contenu) uniquement pour fournir les fonctionnalites de la plateforme. Vous pouvez revoquer l'acces a tout moment.</p>
              <h2 className="text-lg font-semibold text-gray-800 mt-6">6. Conservation</h2>
              <p>Vos donnees sont conservees tant que votre compte est actif. Apres suppression du compte, les donnees sont effacees sous 30 jours.</p>
              <h2 className="text-lg font-semibold text-gray-800 mt-6">7. Vos droits</h2>
              <p>Vous pouvez demander l'acces, la modification ou la suppression de vos donnees a tout moment en contactant : contact@optimusai.app</p>
              <h2 className="text-lg font-semibold text-gray-800 mt-6">8. Contact DPO</h2>
              <p>Pour toute question relative a la protection de vos donnees : dpo@optimusai.app</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
