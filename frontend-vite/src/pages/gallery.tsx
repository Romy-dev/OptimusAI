import { useState } from "react";
import { toast } from "sonner";
import {
  ImageIcon, Loader2, Zap, Sparkles, X, Trash2, Layout,
  Send, Facebook, Instagram, MessageCircle, ExternalLink, FileText,
} from "lucide-react";
import { GenerationProgress } from "@/components/ui/generation-progress";
import { cn } from "@/lib/utils";
import { useApi } from "@/hooks/use-api";
import {
  posts as postsApi,
  brands as brandsApi,
  gallery as galleryApi,
  GalleryImage,
} from "@/lib/api";

type GenMode = "image" | "poster";

export default function GalleryPage() {
  const { data: brandList } = useApi(() => brandsApi.list(), []);
  const { data: savedImages, refetch } = useApi(() => galleryApi.list(), []);

  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState<GenMode>("poster");
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fullscreen, setFullscreen] = useState<GalleryImage | null>(null);
  const [createPostImage, setCreatePostImage] = useState<GalleryImage | null>(null);

  const brandId = brandList?.[0]?.id;

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setGenerating(true);
    setError(null);
    try {
      if (mode === "poster") {
        const result = await postsApi.generatePoster({
          brief: prompt,
          brand_id: brandId,
          aspect_ratio: "1:1",
        });
        if (result.success) {
          toast.success("Affiche marketing generee");
          setPrompt("");
          refetch();
        } else {
          setError(result.error || "Echec de la generation");
        }
      } else {
        const result = await postsApi.generateImage({
          media_suggestion: prompt,
          brand_id: brandId,
          aspect_ratio: "1:1",
        });
        if (result.success) {
          toast.success("Image generee");
          setPrompt("");
          refetch();
        } else {
          setError(result.error || "Echec de la generation");
        }
      }
    } catch (err: any) {
      setError(err.message || "Erreur");
    } finally {
      setGenerating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Supprimer cette image ?")) return;
    try {
      await galleryApi.delete(id);
      toast.success("Image supprimee");
      refetch();
      setFullscreen(null);
    } catch { /* ignore */ }
  };

  const images = savedImages || [];
  const posters = images.filter((i) => i.metadata?.type === "poster");
  const photos = images.filter((i) => i.metadata?.type !== "poster");

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Studio Creatif IA</h1>
        <p className="mt-1 text-sm text-gray-500">
          Generez des visuels marketing et des affiches professionnelles
        </p>
      </div>

      {/* Generator */}
      <div className="surface p-5">
        {/* Mode selector */}
        <div className="flex items-center gap-2 mb-4">
          <button
            onClick={() => setMode("poster")}
            className={cn(
              "flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-all",
              mode === "poster" ? "bg-brand-500 text-white shadow-sm" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            )}
          >
            <Layout className="h-4 w-4" /> Affiche marketing
          </button>
          <button
            onClick={() => setMode("image")}
            className={cn(
              "flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-all",
              mode === "image" ? "bg-brand-500 text-white shadow-sm" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            )}
          >
            <ImageIcon className="h-4 w-4" /> Photo IA
          </button>
        </div>

        <p className="text-xs text-gray-500 mb-3">
          {mode === "poster"
            ? "Decrivez votre affiche : l'IA genere le visuel + titre accrocheur + bouton CTA avec vos couleurs de marque"
            : "Decrivez une image et l'IA la genere avec FLUX"}
        </p>

        <div className="flex gap-3">
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !generating && handleGenerate()}
            placeholder={mode === "poster"
              ? "Ex: Promotion -30% sur la nouvelle collection wax pour la fete des meres..."
              : "Ex: Femme africaine en robe wax dans un marche colore..."
            }
            className="input-base flex-1"
          />
          <button
            onClick={handleGenerate}
            disabled={!prompt.trim() || generating}
            className="btn-primary px-6"
          >
            {generating ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Generation...</>
            ) : mode === "poster" ? (
              <><Layout className="h-4 w-4" /> Creer</>
            ) : (
              <><ImageIcon className="h-4 w-4" /> Generer</>
            )}
          </button>
        </div>

        <GenerationProgress type={mode === "poster" ? "poster" : "image"} active={generating} prompt={prompt || undefined} />

        {error && (
          <div className="mt-3 rounded-xl bg-red-50 border border-red-100 p-3 text-sm text-red-600">
            {error}
          </div>
        )}
      </div>

      {/* Posters section */}
      {posters.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Layout className="h-4 w-4 text-brand-500" />
            <p className="section-label">Affiches marketing ({posters.length})</p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {posters.map((img) => (
              <ImageCard key={img.id} img={img} onView={setFullscreen} onDelete={handleDelete} onCreatePost={setCreatePostImage} />
            ))}
          </div>
        </div>
      )}

      {/* Photos section */}
      {photos.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <ImageIcon className="h-4 w-4 text-purple-500" />
            <p className="section-label">Photos IA ({photos.length})</p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {photos.map((img) => (
              <ImageCard key={img.id} img={img} onView={setFullscreen} onDelete={handleDelete} onCreatePost={setCreatePostImage} />
            ))}
          </div>
        </div>
      )}

      {images.length === 0 && !generating && (
        <div className="surface flex flex-col items-center py-16 text-center">
          <Sparkles className="h-12 w-12 text-gray-200" />
          <p className="mt-4 text-sm font-medium text-gray-500">Votre studio est vide</p>
          <p className="mt-1 text-xs text-gray-400">
            Creez votre premiere affiche marketing ou generez une photo IA
          </p>
        </div>
      )}

      {/* Create post from image modal */}
      {createPostImage && (
        <CreatePostFromImageModal
          image={createPostImage}
          brandId={brandId}
          onClose={() => setCreatePostImage(null)}
        />
      )}

      {/* Fullscreen modal */}
      {fullscreen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={() => setFullscreen(null)}>
          <button onClick={() => setFullscreen(null)} className="absolute top-4 right-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20 transition-colors">
            <X className="h-6 w-6" />
          </button>
          <div className="relative max-h-[90vh] max-w-[90vw]" onClick={(e) => e.stopPropagation()}>
            <img src={fullscreen.image_url} alt={fullscreen.prompt} className="max-h-[85vh] max-w-[90vw] rounded-2xl shadow-2xl" />
            <div className="mt-3 flex items-center justify-between gap-4">
              <div className="min-w-0">
                {fullscreen.metadata?.type === "poster" && (
                  <span className="badge bg-brand-100 text-brand-700 mb-1"><Layout className="h-3 w-3" /> Affiche</span>
                )}
                <p className="text-sm text-white/80 truncate">{fullscreen.prompt}</p>
              </div>
              <button onClick={() => handleDelete(fullscreen.id)} className="rounded-lg bg-red-500/80 px-3 py-1.5 text-xs text-white hover:bg-red-500 transition-colors shrink-0">
                <Trash2 className="h-3.5 w-3.5 inline mr-1" /> Supprimer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ImageCard({ img, onView, onDelete, onCreatePost }: { img: GalleryImage; onView: (img: GalleryImage) => void; onDelete: (id: string) => void; onCreatePost: (img: GalleryImage) => void }) {
  return (
    <div
      className="group relative rounded-2xl overflow-hidden border border-gray-100 shadow-sm hover:shadow-lg transition-all cursor-pointer"
      onClick={() => onView(img)}
    >
      <img src={img.image_url} alt={img.prompt} className="w-full aspect-square object-cover transition-transform duration-300 group-hover:scale-105" />
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
        <div className="absolute bottom-0 left-0 right-0 p-3">
          {img.metadata?.type === "poster" && (
            <span className="inline-flex items-center gap-1 rounded-full bg-brand-500/80 px-2 py-0.5 text-[9px] font-bold text-white mb-1">
              <Layout className="h-2.5 w-2.5" /> AFFICHE
            </span>
          )}
          <p className="text-xs text-white/90 line-clamp-2">{img.prompt}</p>
        </div>
      </div>
      {/* Create post button */}
      <button
        onClick={(e) => { e.stopPropagation(); onCreatePost(img); }}
        className="absolute top-2 left-2 rounded-full bg-brand-500/90 px-2.5 py-1 text-[10px] font-semibold text-white opacity-0 group-hover:opacity-100 hover:bg-brand-600 transition-all flex items-center gap-1 shadow-sm"
      >
        <FileText className="h-3 w-3" /> Creer un post
      </button>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(img.id); }}
        className="absolute top-2 right-2 rounded-full bg-black/40 p-1.5 text-white opacity-0 group-hover:opacity-100 hover:bg-red-500 transition-all"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

const POST_CHANNELS = [
  { key: "facebook", label: "Facebook", icon: Facebook, color: "bg-blue-50 text-blue-600 border-blue-200", activeColor: "bg-blue-600 text-white border-blue-600" },
  { key: "instagram", label: "Instagram", icon: Instagram, color: "bg-pink-50 text-pink-600 border-pink-200", activeColor: "bg-pink-600 text-white border-pink-600" },
  { key: "whatsapp", label: "WhatsApp", icon: MessageCircle, color: "bg-emerald-50 text-emerald-600 border-emerald-200", activeColor: "bg-emerald-600 text-white border-emerald-600" },
];

function CreatePostFromImageModal({
  image,
  brandId,
  onClose,
}: {
  image: GalleryImage;
  brandId?: string;
  onClose: () => void;
}) {
  const [postText, setPostText] = useState(image.prompt || "");
  const [channel, setChannel] = useState("facebook");
  const [creating, setCreating] = useState(false);
  const [createdPostId, setCreatedPostId] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!postText.trim() || !brandId) return;
    setCreating(true);
    try {
      const post = await postsApi.create({
        brand_id: brandId,
        content_text: postText,
        target_channels: [{ channel }],
      });
      // Attach the image to the post
      await postsApi.attachImage(post.id, {
        image_url: image.image_url,
        prompt: image.prompt,
      });
      setCreatedPostId(post.id);
      toast.success("Post cree avec l'image !");
    } catch (err: any) {
      toast.error("Erreur lors de la creation", { description: err.message });
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md mx-4 bg-white rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">Creer un post avec cette image</h2>
          <button onClick={onClose} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {/* Image preview */}
          <div className="rounded-xl overflow-hidden border border-gray-100">
            <img src={image.image_url} alt={image.prompt} className="w-full h-40 object-cover" />
          </div>

          {!createdPostId ? (
            <>
              {/* Post text */}
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1.5 block">Texte du post</label>
                <textarea
                  value={postText}
                  onChange={(e) => setPostText(e.target.value)}
                  rows={4}
                  className="input-base w-full resize-none"
                  placeholder="Ecrivez le texte de votre post..."
                />
                <p className="mt-1 text-[10px] text-gray-400 text-right">{postText.length} caracteres</p>
              </div>

              {/* Channel selector */}
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">Canal</label>
                <div className="flex gap-2">
                  {POST_CHANNELS.map((ch) => {
                    const active = channel === ch.key;
                    return (
                      <button
                        key={ch.key}
                        onClick={() => setChannel(ch.key)}
                        className={cn(
                          "flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium border transition-all",
                          active ? ch.activeColor : ch.color,
                        )}
                      >
                        <ch.icon className="h-4 w-4" />
                        {ch.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Create button */}
              <button
                onClick={handleCreate}
                disabled={creating || !postText.trim()}
                className="btn-primary w-full py-2.5"
              >
                {creating ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /> Creation...</>
                ) : (
                  <><Send className="h-4 w-4" /> Creer le post</>
                )}
              </button>
            </>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-2 rounded-xl bg-emerald-50 border border-emerald-100 p-3">
                <Sparkles className="h-5 w-5 text-emerald-600" />
                <p className="text-sm font-medium text-emerald-700">Post cree avec l'image !</p>
              </div>
              <a
                href="/posts"
                className="flex items-center justify-between rounded-xl border border-gray-200 p-3 hover:bg-gray-50 transition-colors"
              >
                <span className="text-sm text-gray-700">Voir le post</span>
                <ExternalLink className="h-4 w-4 text-gray-400" />
              </a>
              <button onClick={onClose} className="btn-ghost w-full">Fermer</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
