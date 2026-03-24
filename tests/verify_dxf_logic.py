
import sys
import os
import io
import unittest
from unittest.mock import MagicMock
import tempfile
import ezdxf

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock streamlit before importing renderers
st_mock = MagicMock()
sys.modules['streamlit'] = st_mock
sys.modules['streamlit.components'] = MagicMock()
sys.modules['streamlit.components.v1'] = MagicMock()
import streamlit as st

# Import the functions we modified
from utils.renderers import render_dxf

class TestDXFLogic(unittest.TestCase):
    def setUp(self):
        # Create a simple DXF valid content
        self.dxf_content = """  0
SECTION
  2
HEADER
  9
$ACADVER
  1
AC1009
  0
ENDSEC
  0
SECTION
  2
ENTITIES
  0
LINE
  8
0
 10
0.0
 20
0.0
 30
0.0
 11
1.0
 21
1.0
 31
0.0
  0
ENDSEC
  0
EOF
"""
        self.file_buffer = io.BytesIO(self.dxf_content.encode('utf-8'))

    def test_render_dxf(self):
        print("\nTesting render_dxf...")
        try:
            # We just want to ensure it runs without crashing and calls plotly_chart
            self.file_buffer.seek(0)
            render_dxf(self.file_buffer)
            
            # Check if st.plotly_chart was called
            st.plotly_chart.assert_called()
            print("render_dxf executed successfully and called st.plotly_chart")
            
        except Exception as e:
            self.fail(f"render_dxf raised exception: {e}")

if __name__ == '__main__':
    unittest.main()
