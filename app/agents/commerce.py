"""Commerce agent — handles WhatsApp commerce conversations.

Detects purchase intent, shows products, builds carts, handles payments
(Orange Money, Wave, Moov Money), verifies payment screenshots via VLM,
creates orders, and tracks delivery.
"""

import json
import re

import structlog

from app.agents.base import AgentResult, BaseAgent
from app.core.security import PromptSecurity

logger = structlog.get_logger()


class CommerceAgent(BaseAgent):
    name = "commerce"
    description = (
        "Handles WhatsApp commerce: catalog browsing, cart building, "
        "payment instructions, screenshot verification, order creation"
    )
    max_retries = 1
    confidence_threshold = 0.5

    async def execute(self, context: dict) -> AgentResult:
        """Execute commerce logic based on conversation context.

        Context keys:
            customer_phone, message, conversation_history, brand_id, tenant_id,
            brand_context, payment_screenshot (bytes, optional),
            payment_screenshot_url (str, optional)
        """
        from app.integrations.llm import get_llm_router

        customer_message = context.get("customer_message", context.get("message", ""))
        conversation_history = context.get("conversation_history", [])
        brand = context.get("brand_context", {})
        customer_phone = context.get("customer_phone", "")
        customer_name = context.get("customer_name", "")
        channel = context.get("channel", "whatsapp")

        # Sanitize input
        if PromptSecurity.check_injection(customer_message):
            return AgentResult(
                success=True,
                output={
                    "response": "Désolé, je n'ai pas compris votre demande.",
                    "products_shown": [],
                    "order_created": None,
                    "payment_verified": False,
                },
                confidence_score=0.0,
                should_escalate=True,
                escalation_reason="Potential prompt injection detected",
                agent_name=self.name,
            )

        # Check if there's a payment screenshot to verify
        payment_screenshot = context.get("payment_screenshot")
        if payment_screenshot:
            return await self._verify_payment_screenshot(
                context, payment_screenshot
            )

        # Build product catalog section
        products_section = self._format_products(brand.get("products", []))

        # Format conversation history
        history_text = self._format_history(conversation_history)

        # Build the LLM prompt
        system_prompt = self._build_system_prompt(
            brand_name=brand.get("brand_name", "la boutique"),
            tone=brand.get("tone", "professionnel et chaleureux"),
            language=brand.get("language", "français"),
            products_section=products_section,
            customer_name=customer_name,
            customer_phone=customer_phone,
        )

        user_prompt = self._build_user_prompt(
            customer_message=PromptSecurity.sanitize_for_prompt(customer_message),
            history_text=history_text,
        )

        llm = get_llm_router()
        response = await llm.generate(
            task_type="commerce",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        parsed = self._parse_llm_output(response.content)

        response_text = parsed.get("response", "")
        products_shown = parsed.get("products_shown", [])
        order_created = parsed.get("order_created", None)
        action = parsed.get("action", "chat")
        confidence = max(0.0, min(1.0, parsed.get("confidence", 0.7)))

        return AgentResult(
            success=True,
            output={
                "response": response_text,
                "products_shown": products_shown,
                "order_created": order_created,
                "payment_verified": False,
                "action": action,
                "channel": channel,
            },
            confidence_score=confidence,
            agent_name=self.name,
            tokens_used=response.tokens_used,
            model_used=response.model,
        )

    async def _verify_payment_screenshot(
        self, context: dict, image_data: bytes
    ) -> AgentResult:
        """Use VLM to analyze a payment screenshot and verify the amount."""
        from app.integrations.vlm import get_vlm_router

        expected_amount = context.get("expected_amount", 0)
        currency = context.get("currency", "XOF")
        payment_method = context.get("payment_method", "")

        prompt = (
            f"Analyse cette capture d'écran de paiement mobile ({payment_method}).\n"
            f"Montant attendu: {expected_amount} {currency}\n\n"
            "Réponds en JSON avec ces champs:\n"
            '- "amount_detected": le montant visible sur la capture (nombre)\n'
            '- "currency_detected": la devise visible\n'
            '- "transaction_id": le numéro de transaction si visible\n'
            '- "sender": le nom ou numéro de l\'expéditeur si visible\n'
            '- "recipient": le nom ou numéro du destinataire si visible\n'
            '- "status": "success" ou "failed" selon ce que montre la capture\n'
            '- "amount_matches": true si le montant correspond au montant attendu\n'
            '- "is_valid_payment": true si tout semble correct\n'
            '- "confidence": score de confiance entre 0 et 1\n'
            '- "notes": observations supplémentaires\n'
        )

        system = (
            "Tu es un expert en vérification de paiements mobiles en Afrique de l'Ouest. "
            "Tu analyses des captures d'écran de paiements Orange Money, Moov Money et Wave. "
            "Sois rigoureux sur la vérification des montants. "
            "Réponds UNIQUEMENT en JSON valide."
        )

        vlm = get_vlm_router()
        vlm_response = await vlm.analyze_image(
            image_data=image_data,
            prompt=prompt,
            system=system,
        )

        parsed = self._parse_llm_output(vlm_response.content)

        amount_matches = parsed.get("amount_matches", False)
        is_valid = parsed.get("is_valid_payment", False)
        vlm_confidence = parsed.get("confidence", 0.0)

        payment_verified = bool(amount_matches and is_valid and vlm_confidence >= 0.7)

        if payment_verified:
            response_text = (
                f"Paiement vérifié avec succès ! "
                f"Montant: {parsed.get('amount_detected', expected_amount)} {currency}. "
                f"Votre commande est confirmée. Merci !"
            )
        else:
            response_text = (
                "Nous n'avons pas pu vérifier le paiement automatiquement. "
                "Un membre de notre équipe va vérifier manuellement. "
                "Merci de votre patience !"
            )

        return AgentResult(
            success=True,
            output={
                "response": response_text,
                "products_shown": [],
                "order_created": None,
                "payment_verified": payment_verified,
                "payment_details": parsed,
                "action": "payment_verification",
            },
            confidence_score=vlm_confidence,
            should_escalate=not payment_verified,
            escalation_reason=(
                "Payment verification failed — manual review needed"
                if not payment_verified
                else None
            ),
            agent_name=self.name,
            tokens_used=vlm_response.tokens_used,
            model_used=vlm_response.model,
        )

    def _format_products(self, products: list[dict]) -> str:
        if not products:
            return "Aucun produit disponible dans le catalogue."
        lines = []
        for p in products:
            price = p.get("price", "prix non communiqué")
            currency = p.get("currency", "XOF")
            name = p.get("name", "")
            desc = p.get("description", "")
            category = p.get("category", "")
            in_stock = p.get("in_stock", True)
            stock_status = "En stock" if in_stock else "Rupture de stock"
            line = f"- {name}: {desc}"
            if category:
                line += f" (catégorie: {category})"
            line += f" — {price} {currency} [{stock_status}]"
            lines.append(line)
        return "\n".join(lines)

    def _format_history(self, history: list[dict]) -> str:
        if not history:
            return ""
        lines = []
        for msg in history[-10:]:
            role = "Client" if msg.get("direction") == "inbound" else "Boutique"
            lines.append(f"{role}: {msg.get('content', '')}")
        return "\n".join(lines)

    def _build_system_prompt(
        self,
        brand_name: str,
        tone: str,
        language: str,
        products_section: str,
        customer_name: str,
        customer_phone: str,
    ) -> str:
        return f"""Tu es l'assistant commercial de {brand_name} sur WhatsApp.

TON RÔLE:
- Aider les clients à découvrir et acheter des produits
- Montrer les produits du catalogue quand le client cherche quelque chose
- Construire un panier et calculer le total
- Donner les instructions de paiement (Orange Money, Moov Money, Wave, Cash)
- Confirmer les commandes

STYLE: {tone}
LANGUE: {language}

CATALOGUE DE PRODUITS:
{products_section}

CLIENT: {customer_name or 'Client'} ({customer_phone})

MÉTHODES DE PAIEMENT ACCEPTÉES:
- Orange Money: Envoyer au *XX XX XX XX XX* (nom: {brand_name})
- Moov Money: Envoyer au *XX XX XX XX XX* (nom: {brand_name})
- Wave: Envoyer au *XX XX XX XX XX* (nom: {brand_name})
- Cash: Paiement à la livraison

RÈGLES:
1. Sois naturel et conversationnel — c'est WhatsApp, pas un email formel
2. Quand le client demande des produits, montre-les avec prix en XOF (FCFA)
3. Quand le client veut commander, récapitule le panier avec le total
4. Après confirmation du panier, donne les instructions de paiement
5. Ne propose que des produits du catalogue
6. Si un produit est en rupture, propose des alternatives
7. Utilise des emojis avec modération (c'est WhatsApp)

RÉPONDS EN JSON avec ces champs:
- "response": ta réponse au client (texte WhatsApp)
- "products_shown": liste des noms de produits montrés ([] si aucun)
- "order_created": null ou un objet avec "items" (liste de {{product_name, qty, price}}), "total", "currency"
- "action": "browse" | "show_products" | "build_cart" | "payment_instructions" | "confirm_order" | "chat"
- "confidence": score de confiance entre 0 et 1
"""

    def _build_user_prompt(self, customer_message: str, history_text: str) -> str:
        prompt = ""
        if history_text:
            prompt += f"HISTORIQUE DE LA CONVERSATION:\n{history_text}\n\n"
        prompt += f"NOUVEAU MESSAGE DU CLIENT:\n{customer_message}"
        return prompt

    @staticmethod
    def _parse_llm_output(raw: str) -> dict:
        """Robustly parse LLM JSON output with fallbacks."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in the text
        json_match = re.search(r"\{[\s\S]*\}", cleaned)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        logger.warning("commerce_agent_parse_failed", raw_length=len(raw))
        return {
            "response": raw[:500] if raw else "Désolé, je n'ai pas compris. Pouvez-vous reformuler ?",
            "products_shown": [],
            "order_created": None,
            "action": "chat",
            "confidence": 0.3,
        }

    async def validate_output(self, result: AgentResult) -> bool:
        """Validate that the output has the required structure."""
        output = result.output
        if "response" not in output:
            return False
        if not isinstance(output.get("products_shown"), list):
            return False
        if "payment_verified" not in output:
            return False
        return True
