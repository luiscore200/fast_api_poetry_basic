from typing import List,Dict, Union

def flatten_metadata_list(
    prefix: str,
    items: List[Union[str, int, float, bool]]
) -> Dict[str, Union[str, int, float, bool]]:
    """
    Convierte una lista en un diccionario con claves numeradas.

    Ejemplo:
        prefix='merged_tag', items=['a', 'b']
        => {'merged_tag_0': 'a', 'merged_tag_1': 'b'}
    """
    return {f"{prefix}_{i}": item for i, item in enumerate(items)}
