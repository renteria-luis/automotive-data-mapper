# Notebooks

Where the work starts. A notebook is for figuring out what the code should do: reading a feed,
looking at what is malformed in it, trying a transformation and checking the result by eye.

Once something works and stops changing, it moves into `src/` as a function with a test, and the
notebook imports it instead of redefining it. The notebook keeps the exploration and the numbers;
`src/` keeps the code that runs.

The project is installed in editable mode by `make install`, so an import works from any notebook
without touching `sys.path`:

```python
from src.models import VehicleEvent, RejectedRecord, ReasonCode
```

Restart the kernel after moving code into `src/`, or the notebook keeps running the old version.
