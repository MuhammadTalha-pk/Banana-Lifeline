from .rag_service import index_knowledge


if __name__ == '__main__':
    count = index_knowledge(recreate=True)
    print(f'Indexed {count} knowledge chunks.')
