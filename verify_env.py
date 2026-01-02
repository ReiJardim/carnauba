import ezdxf
import ifcopenshell
import pypdf
import streamlit
import matplotlib

print("Imports successful:")
print(f"ezdxf: {ezdxf.__version__}")
print(f"ifcopenshell schema: {ifcopenshell.schema_by_name('IFC4').name() if hasattr(ifcopenshell, 'schema_by_name') else 'Available'}")
print(f"pypdf: {pypdf.__version__}")
print(f"streamlit: {streamlit.__version__}")
