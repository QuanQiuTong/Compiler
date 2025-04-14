// all kinds of function declaration

// function declaration
function add(a: number, b: number): number {
    return a + b;
}

// no return type
function sub(a: number, b: number) {
    return a - b;
}

// no parameter type
function mul(a, b): number {
    return a * b;
}

// no return type and parameter type
function div(a, b) {
    return a / b;
}

// function expression
const mod = function (a: number, b: number): number {
    return a % b;
}

// arrow function
const pow = (a: number, b: number): number => {
    return a ** b;
}

// async function
async function asyncFunc(a: number, b: number): Promise<number> {
    return a + b;
}

