"""
Smart Store - Phase 3
User-friendly, bilingual (English / French) notifications for every action.

In a Flask route:

    from notifications import notify
    ...
    db.add_product(...)
    return jsonify(notify("product_added", lang, name=name))
    # -> {"success": true, "level": "success",
    #     "message": "Product \"Coca-Cola 500ml\" added successfully.",
    #     "message_en": "...", "message_fr": "..."}

On error:

    except db.DatabaseError as error:
        return jsonify(notify_error(str(error), lang)), 400

The front end just shows `message` in a toast/banner coloured by `level`.
Every notification is also saved in the `notifications` table.
"""

import db

# key: (level, English, French). {placeholders} are filled from notify(**kwargs).
MESSAGES = {
    # --- Product management ---
    "product_added": ("success",
        'Product "{name}" added successfully.',
        'Produit « {name} » ajouté avec succès.'),
    "product_updated": ("success",
        'Product "{name}" updated successfully.',
        'Produit « {name} » modifié avec succès.'),
    "product_deleted": ("success",
        'Product "{name}" deleted.',
        'Produit « {name} » supprimé.'),
    "stock_received": ("success",
        "Received {quantity} x {name}. Now {in_stock} in stock.",
        "{quantity} x {name} reçu(s). {in_stock} en stock."),
    "low_stock": ("warning",
        'Low stock: only {in_stock} "{name}" left.',
        'Stock faible : il reste seulement {in_stock} « {name} ».'),

    # --- Scanning ---
    "item_scanned": ("info",
        "{name} added to your list.",
        "{name} ajouté à votre liste."),
    "items_scanned": ("info",
        "{count} item(s) detected.",
        "{count} article(s) détecté(s)."),
    "unknown_tag": ("warning",
        "Unknown item (code {code}). Please ask an employee.",
        "Article inconnu (code {code}). Veuillez demander à un employé."),
    "item_removed": ("info",
        "{name} removed from your list.",
        "{name} retiré de votre liste."),

    # --- Checkout ---
    "member_found": ("success",
        "Welcome back, {name}! You have {points} points.",
        "Bon retour, {name} ! Vous avez {points} points."),
    "member_not_found": ("warning",
        "Membership card not found. You can continue as a guest.",
        "Carte de membre introuvable. Vous pouvez continuer en tant qu'invité."),
    "payment_approved": ("success",
        "Payment of ${total:.2f} approved.",
        "Paiement de {total} $ approuvé."),
    "checkout_completed": ("success",
        "Checkout completed! Receipt {receipt_number}. You earned {points} points.",
        "Paiement terminé ! Reçu {receipt_number}. Vous avez gagné {points} points."),
    "checkout_completed_guest": ("success",
        "Checkout completed! Receipt {receipt_number}.",
        "Paiement terminé ! Reçu {receipt_number}."),

    # --- Receipts ---
    "receipt_emailed": ("success",
        "Receipt sent to {email}.",
        "Reçu envoyé à {email}."),
    "receipt_email_failed": ("warning",
        "The receipt could not be emailed, but your purchase is saved.",
        "Le reçu n'a pas pu être envoyé par courriel, mais votre achat est enregistré."),

    # --- Accounts ---
    "account_created": ("success",
        "Account created! Your membership number is {membership_number}.",
        "Compte créé ! Votre numéro de membre est {membership_number}."),
    "login_success": ("success",
        "Welcome, {name}!",
        "Bienvenue, {name} !"),
    "login_failed": ("error",
        "Wrong email or password.",
        "Courriel ou mot de passe incorrect."),
    "logged_out": ("info",
        "You have been logged out.",
        "Vous avez été déconnecté."),
}

# French versions of the DatabaseError messages raised in db.py
ERROR_TRANSLATIONS = {
    "Name, category and producer are required.": "Le nom, la catégorie et le producteur sont obligatoires.",
    "Price must be a number.": "Le prix doit être un nombre.",
    "Price can't be negative.": "Le prix ne peut pas être négatif.",
    "UPC is required and must be at most 13 characters.": "Le CUP est obligatoire (13 caractères maximum).",
    "EPC must be at most 24 characters.": "L'EPC doit contenir au plus 24 caractères.",
    "A product with this UPC already exists.": "Un produit avec ce CUP existe déjà.",
    "A product with this EPC already exists.": "Un produit avec cet EPC existe déjà.",
    "Product not found.": "Produit introuvable.",
    "Quantity must be a whole number.": "La quantité doit être un nombre entier.",
    "Quantity must be greater than 0.": "La quantité doit être supérieure à 0.",
    "Quantities must be greater than 0.": "Les quantités doivent être supérieures à 0.",
    "The shopping list is empty.": "La liste d'achats est vide.",
    "Customer not found.": "Client introuvable.",
    "Name, email and password are required.": "Le nom, le courriel et le mot de passe sont obligatoires.",
    "Enter a valid email address.": "Entrez une adresse courriel valide.",
    "Password must be at least 6 characters.": "Le mot de passe doit contenir au moins 6 caractères.",
    "An account with this email already exists.": "Un compte avec ce courriel existe déjà.",
    "Select a valid product.": "Sélectionnez un produit valide.",
    "Quantity must be greater than zero.": "La quantité doit être supérieure à zéro.",
    "Enter a valid reception date and time.": "Entrez une date et une heure de réception valides.",
}


def _pick(lang, en, fr):
    return fr if lang == "fr" else en


def notify(key, lang="en", save=True, **values):
    """Build (and log) a notification for an action. Returns a dict ready for jsonify()."""
    level, en, fr = MESSAGES[key]
    message_en = en.format(**values)
    # French writes money with a comma: 13,17 $
    values_fr = {
        k: (f"{v:.2f}".replace(".", ",") if isinstance(v, float) else v)
        for k, v in values.items()
    }
    message_fr = fr.format(**values_fr)
    if save:
        db.save_notification(level, message_en, message_fr)
    return {
        "success": level in ("success", "info"),
        "level": level,
        "message": _pick(lang, message_en, message_fr),
        "message_en": message_en,
        "message_fr": message_fr,
    }


def notify_error(message_en, lang="en", save=True):
    """Wrap an error (usually str(DatabaseError)) as a notification."""
    message_fr = ERROR_TRANSLATIONS.get(message_en, message_en)
    if save:
        db.save_notification("error", message_en, message_fr)
    return {
        "success": False,
        "level": "error",
        "message": _pick(lang, message_en, message_fr),
        "message_en": message_en,
        "message_fr": message_fr,
    }
