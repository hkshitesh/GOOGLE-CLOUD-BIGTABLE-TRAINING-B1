import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.cloud import bigtable


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
INSTANCE_ID = os.environ["INSTANCE_ID"]
TABLE_ID = os.environ["TABLE_ID"]

# Existing column family
COLUMN_FAMILY = "metrics"

# ------------------------------------------------------------
# Load configuration
# ------------------------------------------------------------

# Total number of unique rows
TOTAL_ROWS = 100000

# Payload size per row
# 50 KB
PAYLOAD_SIZE = 50 * 1024

# Rows written in one Bigtable batch
BATCH_SIZE = 100

# Number of concurrent workers
WORKERS = 10


# ============================================================
# BIGTABLE CONNECTION
# ============================================================

print("Connecting to Bigtable...")

client = bigtable.Client(
    project=PROJECT_ID,
    admin=True
)

instance = client.instance(INSTANCE_ID)

table = instance.table(TABLE_ID)

print("Connected.")
print()


# ============================================================
# GENERATE RANDOM PAYLOAD
# ============================================================
#
# IMPORTANT:
# Do NOT use:
#
#     b"X" * PAYLOAD_SIZE
#
# because repetitive data compresses very well.
#
# os.urandom() generates random bytes and gives us a much
# more realistic payload.
# ============================================================

print("Generating random payload...")

payload = os.urandom(PAYLOAD_SIZE)

print(
    f"Payload size: "
    f"{len(payload) / 1024:.2f} KB"
)

print()


# ============================================================
# LOAD INFORMATION
# ============================================================

expected_gb = (
    TOTAL_ROWS * PAYLOAD_SIZE
) / (1024 ** 3)

print("==========================================")
print("       BIGTABLE HEAVY LOAD TEST")
print("==========================================")
print(f"Project         : {PROJECT_ID}")
print(f"Instance        : {INSTANCE_ID}")
print(f"Table           : {TABLE_ID}")
print(f"Rows            : {TOTAL_ROWS:,}")
print(
    f"Payload / row   : "
    f"{PAYLOAD_SIZE / 1024:.0f} KB"
)
print(
    f"Expected payload: "
    f"~{expected_gb:.2f} GB"
)
print(f"Batch size      : {BATCH_SIZE}")
print(f"Workers         : {WORKERS}")
print("Hotspot range   : hotspot#001 - hotspot#100")
print("==========================================")
print()


# ============================================================
# WRITE ONE BATCH
# ============================================================

def write_batch(batch_number):

    start = batch_number * BATCH_SIZE

    end = min(
        start + BATCH_SIZE,
        TOTAL_ROWS
    )

    rows = []

    for i in range(start, end):

        # ----------------------------------------------------
        # HOTSPOT
        # ----------------------------------------------------
        #
        # Only 100 sensor IDs are used.
        #
        # Therefore traffic is concentrated into:
        #
        # hotspot#001
        # hotspot#002
        # ...
        # hotspot#100
        #
        # But a timestamp + counter makes every row unique.
        # ----------------------------------------------------

        sensor_id = random.randint(1, 100)

        timestamp = time.time_ns()

        row_key = (
            f"hotspot#"
            f"{sensor_id:03d}"
            f"#"
            f"{timestamp}"
            f"#"
            f"{i}"
        )

        # Create Bigtable row
        r = table.direct_row(row_key)

        # ----------------------------------------------------
        # SMALL COLUMN 1
        # ----------------------------------------------------

        r.set_cell(
            COLUMN_FAMILY,
            "temperature",
            str(random.randint(20, 35))
        )

        # ----------------------------------------------------
        # SMALL COLUMN 2
        # ----------------------------------------------------

        r.set_cell(
            COLUMN_FAMILY,
            "status",
            "ONLINE"
        )

        # ----------------------------------------------------
        # SMALL COLUMN 3
        # ----------------------------------------------------

        r.set_cell(
            COLUMN_FAMILY,
            "location",
            "DEHRADUN"
        )

        # ----------------------------------------------------
        # LARGE 50 KB COLUMN
        # ----------------------------------------------------

        r.set_cell(
            COLUMN_FAMILY,
            "payload",
            payload
        )

        rows.append(r)

    # --------------------------------------------------------
    # BATCH WRITE
    # --------------------------------------------------------

    results = table.mutate_rows(rows)

    # --------------------------------------------------------
    # CHECK RESULTS
    # --------------------------------------------------------

    successful = 0
    errors = 0

    for result in results:

        # In your installed Bigtable client,
        # result.code is an integer.
        #
        # 0 = OK
        #

        if result.code == 0:
            successful += 1
        else:
            errors += 1

    return successful, errors


# ============================================================
# LOAD TEST
# ============================================================

total_batches = (
    TOTAL_ROWS + BATCH_SIZE - 1
) // BATCH_SIZE


start_time = time.time()

successful_rows = 0
failed_rows = 0

completed_batches = 0


print("Starting load test...")
print()
print("Press CTRL+C to stop.")
print()


# ============================================================
# PARALLEL EXECUTION
# ============================================================

try:

    with ThreadPoolExecutor(
        max_workers=WORKERS
    ) as executor:

        futures = []

        for batch_number in range(total_batches):

            future = executor.submit(
                write_batch,
                batch_number
            )

            futures.append(future)


        # ----------------------------------------------------
        # COLLECT RESULTS
        # ----------------------------------------------------

        for future in as_completed(futures):

            successful, errors = future.result()

            successful_rows += successful

            failed_rows += errors

            completed_batches += 1


            # ------------------------------------------------
            # DISPLAY PROGRESS
            # ------------------------------------------------

            if (
                completed_batches % 10 == 0
                or completed_batches == total_batches
            ):

                elapsed = (
                    time.time() - start_time
                )

                if elapsed > 0:

                    rows_per_second = (
                        successful_rows /
                        elapsed
                    )

                else:

                    rows_per_second = 0


                data_gb = (
                    successful_rows *
                    PAYLOAD_SIZE
                ) / (1024 ** 3)


                print(
                    f"Batches: "
                    f"{completed_batches:,}/"
                    f"{total_batches:,} | "
                    f"Rows: "
                    f"{successful_rows:,} | "
                    f"Errors: "
                    f"{failed_rows:,} | "
                    f"Data: "
                    f"{data_gb:.2f} GB | "
                    f"Rate: "
                    f"{rows_per_second:,.0f} rows/sec"
                )


except KeyboardInterrupt:

    print()
    print("CTRL+C detected.")
    print("Stopping load test...")


# ============================================================
# FINAL RESULTS
# ============================================================

elapsed = time.time() - start_time


if elapsed > 0:

    rows_per_second = (
        successful_rows /
        elapsed
    )

else:

    rows_per_second = 0


actual_data_gb = (
    successful_rows *
    PAYLOAD_SIZE
) / (1024 ** 3)


print()
print()
print("==========================================")
print("          LOAD TEST COMPLETED")
print("==========================================")
print(
    f"Successful rows : "
    f"{successful_rows:,}"
)
print(
    f"Failed rows     : "
    f"{failed_rows:,}"
)
print(
    f"Payload / row   : "
    f"{PAYLOAD_SIZE / 1024:.0f} KB"
)
print(
    f"Logical payload : "
    f"~{actual_data_gb:.2f} GB"
)
print(
    f"Elapsed time    : "
    f"{elapsed:.2f} seconds"
)
print(
    f"Write rate      : "
    f"{rows_per_second:,.0f} rows/sec"
)
print("==========================================")
