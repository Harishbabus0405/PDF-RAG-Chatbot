class SourceHandler:
    """Formats source documents into clean citations."""

    @staticmethod
    def extract_citations(source_documents: list) -> list[dict]:
        citations = []
        seen = set()

        for document in source_documents:
            source_name = document.metadata.get("source", "Unknown")
            page_number = SourceHandler._get_page_number(document.metadata)
            citation_key = (source_name, page_number)

            if citation_key in seen:
                continue

            seen.add(citation_key)
            citations.append(
                {
                    "source": source_name,
                    "page": page_number,
                }
            )

        return citations

    @staticmethod
    def _get_page_number(metadata: dict) -> int | str:
        page = metadata.get("page")
        if isinstance(page, int):
            return page + 1
        return "Unknown"
