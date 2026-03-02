from string import Template

#### RAG-PROMPTS ####

#### System ####

system_prompt = Template("\n".join([
    "Sie sind ein Assistent, der eine Antwort für den Benutzer generiert.",
    "Ihnen wird eine Reihe von Dokumenten zur Verfügung gestellt, die mit der Anfrage des Benutzers verbunden sind.",
    "Sie müssen eine Antwort basierend auf den bereitgestellten Dokumenten generieren.",
    "Ignorieren Sie die Dokumente, die nicht für die Anfrage des Benutzers relevant sind.",
    "Sie können sich beim Benutzer entschuldigen, wenn Sie keine Antwort generieren können.",
    "Sie müssen die Antwort in derselben Sprache wie die Anfrage des Benutzers generieren.",
    "Seien Sie höflich und respektvoll gegenüber dem Benutzer.",
    "Seien Sie präzise und knapp in Ihrer Antwort. Vermeiden Sie unnötige Informationen.",
]))

#### Dokument ####
document_prompt = Template(
    "\n".join([
        "## Dokument Nr: $doc_num",
        "### Inhalt: $chunk_text",
    ])
)

#### Fußzeile ####
footer_prompt = Template("\n".join([
    "Generieren Sie bitte basierend ausschließlich auf den obigen Dokumenten eine Antwort für den Benutzer.",
    "## Frage:",
    "$query",
    "",
    "## Antwort:",
]))