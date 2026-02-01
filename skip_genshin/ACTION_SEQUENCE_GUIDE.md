# Action Sequence Interpreter - Advanced Features

## Basic Commands

- **click** - Click at configured position
- **key** - Press a key (e.g., `e`, `space`, `escape`, `enter`)
- **wait:N** - Wait N milliseconds (e.g., `wait:100`)

## Variables

Store and use values throughout your sequence.

```
set count 5
set flag true
set delay 100
```

Access variables with `$` prefix:
```
wait:$delay
if $count > 0
  click
endif
```

## Loops

Repeat a block of commands.

### Fixed loop count:
```
loop 3
  space
  wait:50
  e
endloop
```

### Variable-based loop:
```
set iterations 5
loop $iterations
  click
  wait:100
endloop
```

## Conditionals

Execute code based on conditions.

### Supported operators:
- `>` greater than
- `<` less than
- `>=` greater or equal
- `<=` less or equal
- `==` equals
- `!=` not equals

### Example:
```
set attempts 3
if $attempts > 0
  e
  set attempts 0
endif
```

## Complex Examples

### Repeat dialogue skip 5 times with delay:
```
set count 5
loop $count
  space
  wait:50
  e
  wait:100
endloop
```

### Conditional click:
```
set can_click 1
if $can_click == 1
  click
endif
```

### Nested loops:
```
set outer 2
loop $outer
  set inner 3
  loop $inner
    space
    wait:50
  endloop
  wait:200
endloop
```

### Sequential automation with delays:
```
set step 0
set step 1
wait:200
set step 2
click
wait:100
set step 3
e
```

## Tips

1. **Variables are case-sensitive** - `$Count` and `$count` are different
2. **All conditions are trimmed** - Extra spaces are okay
3. **Comments start with #** - Lines starting with # are ignored
4. **Nested blocks are supported** - Loops and ifs can contain each other
5. **Math operations not supported** - Use `set` to create new values

## Debugging

Use the log in "Activity Log" tab to see execution status. The interpreter will skip invalid commands gracefully.
