using GLib;
using Json;

const int SIZE = 9;
const int BIT_SIZE = 1 << SIZE;
const int WILDCARD = -1;

public class KakurasuSolver : GLib.Object
{
    private int[] row_targets;
    private int[] col_targets;

    private int[,] grid;

    private int[] row_sums;
    private int[] col_sums;

    private bool[] row_solved;

    public uint64 recursions = 0;
    public uint64 backtracks = 0;

    private int[] mask_sum = new int[BIT_SIZE];

    private int[,] domains = new int[SIZE, BIT_SIZE];
    private int[] domain_size = new int[SIZE];

    private bool[,] row_col_possible =
        new bool[SIZE, SIZE];

    private bool[,] row_col_mandatory =
        new bool[SIZE, SIZE];

    private int[] row_values;
    private int[] bit_values;

    private int64 start_time;

    public KakurasuSolver(int[] rows, int[] cols)
    {
        row_targets = rows.copy();
        col_targets = cols.copy();

        grid = new int[SIZE, SIZE];

        row_sums = new int[SIZE];
        col_sums = new int[SIZE];

        row_solved = new bool[SIZE];

        row_values = new int[SIZE];
        bit_values = new int[SIZE];

        for (int i = 0; i < SIZE; i++)
        {
            row_values[i] = i + 1;
            bit_values[i] = 1 << i;
        }

        build_mask_sum();
        build_domains();
        build_constraints();

        start_time = GLib.get_monotonic_time();
    }

    private void build_mask_sum()
    {
        for (int mask = 0; mask < BIT_SIZE; mask++)
        {
            int sum = 0;

            for (int bit = 0; bit < SIZE; bit++)
            {
                if ((mask & (1 << bit)) != 0)
                    sum += bit + 1;
            }

            mask_sum[mask] = sum;
        }
    }

    private void build_domains()
    {
        for (int row = 0; row < SIZE; row++)
        {
            int target = row_targets[row];

            int count = 0;

            for (int mask = 0; mask < BIT_SIZE; mask++)
            {
                if (target == WILDCARD ||
                    mask_sum[mask] == target)
                {
                    domains[row, count] = mask;
                    count++;
                }
            }

            domain_size[row] = count;
        }
    }

    private void build_constraints()
    {
        for (int row = 0; row < SIZE; row++)
        {
            for (int col = 0; col < SIZE; col++)
            {
                bool possible = false;
                bool mandatory = true;

                for (int i = 0;
                     i < domain_size[row];
                     i++)
                {
                    int mask = domains[row, i];

                    bool present =
                        (mask & (1 << col)) != 0;

                    if (present)
                        possible = true;
                    else
                        mandatory = false;
                }

                row_col_possible[row,col] =
                    possible;

                row_col_mandatory[row,col] =
                    mandatory;
            }
        }
    }

    private int choose_row()
    {
        int best_row = -1;
        int best_size = 999999;

        for (int row = 0; row < SIZE; row++)
        {
            if (!row_solved[row])
            {
                int size = domain_size[row];

                if (size < best_size)
                {
                    best_size = size;
                    best_row = row;
                }
            }
        }

        return best_row;
    }

    private void apply_row(int row, int mask)
    {
        for (int bit = 0; bit < SIZE; bit++)
        {
            if ((mask & (1 << bit)) != 0)
            {
                grid[row, bit] = 1;

                row_sums[row] += bit + 1;
                col_sums[bit] += row + 1;
            }
        }
    }

    private void remove_row(int row, int mask)
    {
        for (int bit = 0; bit < SIZE; bit++)
        {
            if ((mask & (1 << bit)) != 0)
            {
                grid[row, bit] = 0;

                row_sums[row] -= bit + 1;
                col_sums[bit] -= row + 1;
            }
        }
    }

    private bool columns_possible()
    {
        for (int col = 0; col < SIZE; col++)
        {
            int target = col_targets[col];

            if (target == WILDCARD)
                continue;

            int current = col_sums[col];

            if (current > target)
                return false;

            if (current == target)
            {
                for (int row = 0; row < SIZE; row++)
                {
                    if (row_solved[row])
                        continue;

                    if (row_col_mandatory[row,col])
                        return false;
                }

                continue;
            }

            int min_possible = current;
            int max_possible = current;

            for (int row = 0; row < SIZE; row++)
            {
                if (row_solved[row])
                    continue;

                int value = row_values[row];

                if (row_col_possible[row,col])
                    max_possible += value;

                if (row_col_mandatory[row,col])
                    min_possible += value;
            }

            if (target < min_possible)
                return false;

            if (target > max_possible)
                return false;
        }

        return true;
    }

    private bool final_validation()
    {
        for (int r = 0; r < SIZE; r++)
        {
            int target = row_targets[r];

            if (target == WILDCARD)
                continue;

            if (row_sums[r] != target)
                return false;
        }

        for (int c = 0; c < SIZE; c++)
        {
            int target = col_targets[c];

            if (target == WILDCARD)
                continue;

            if (col_sums[c] != target)
                return false;
        }

        return true;
    }

    public bool solve()
    {
        recursions++;

        int row = choose_row();

        if (row == -1)
            return final_validation();

        for (int i = 0;
             i < domain_size[row];
             i++)
        {
            int mask = domains[row, i];

            apply_row(row, mask);

            row_solved[row] = true;

            if (columns_possible())
            {
                if (solve())
                    return true;
            }

            row_solved[row] = false;

            remove_row(row, mask);

            backtracks++;
        }

        return false;
    }

    public void print_solution()
    {
        stdout.printf("\n");

        for (int r = 0; r < SIZE; r++)
        {
            for (int c = 0; c < SIZE; c++)
            {
                stdout.printf(
                    "%s ",
                    grid[r,c] == 1 ? "■" : "·"
                );
            }

            stdout.printf("\n");
        }

        double elapsed = elapsed_time();

        stdout.printf("\n");
        stdout.printf("Rekursioner: %" + uint64.FORMAT + "\n",
                      recursions);
        stdout.printf("Backtracks: %" + uint64.FORMAT + "\n",
                      backtracks);
        stdout.printf("Tid: %.4f s\n",
                      elapsed);
    }

    public void print_json()
    {
        stdout.printf("{");
        stdout.printf("\"ok\":true,");

        stdout.printf("\"grid\":[");

        for (int r = 0; r < SIZE; r++)
        {
            stdout.printf("[");

            for (int c = 0; c < SIZE; c++)
            {
                stdout.printf("%d", grid[r,c]);

                if (c < SIZE - 1)
                    stdout.printf(",");
            }

            stdout.printf("]");

            if (r < SIZE - 1)
                stdout.printf(",");
        }

        stdout.printf("],");

        stdout.printf("\"recursions\":%" + uint64.FORMAT + ",",
            recursions);

        stdout.printf("\"backtracks\":%" + uint64.FORMAT + ",",
            backtracks);

        stdout.printf("\"time\":%.6f",
            elapsed_time());

        stdout.printf("}\n");
    }
    
    public double elapsed_time()
    {
        return ((double)
            (GLib.get_monotonic_time() - start_time))
            / 1000000.0;
    }
}

public static int main()
{
    StringBuilder input = new StringBuilder();

    string? line;

    while ((line = stdin.read_line()) != null)
    {
        input.append(line);
    }

    string json_text = input.str;

    var parser = new Json.Parser();

    parser.load_from_data(json_text);

    var root = parser.get_root();

    var obj = root.get_object();

    int[] rows = new int[SIZE];

    var rows_array =
        obj.get_array_member("rows");

    for (int i = 0; i < SIZE; i++)
    {
        rows[i] =
            (int) rows_array.get_int_element(i);
    }

    int[] cols = new int[SIZE];

    var cols_array =
        obj.get_array_member("cols");

    for (int i = 0; i < SIZE; i++)
    {
        cols[i] =
            (int) cols_array.get_int_element(i);
    }

    var solver =
        new KakurasuSolver(rows, cols);

    if (solver.solve())
    {
        solver.print_json();
    }
    else
    {
        stdout.printf("{\"ok\":false,");
        stdout.printf("\"grid\":[],");
        stdout.printf("\"recursions\":%" + uint64.FORMAT + ",",
            solver.recursions);
        stdout.printf("\"backtracks\":%" + uint64.FORMAT + ",",
            solver.backtracks);
        stdout.printf("\"time\":%.6f}\n", solver.elapsed_time());
    }

    return 0;
}
