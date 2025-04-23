class Person  {
    // 成员变量
    firstName: string;
    public lastName: string
    public age: number;
    
    // 构造函数
    constructor( firstName: string, lastName: string, age: number) {
      this.firstName = firstName;
      this.lastName = lastName;
      this.age = age;
    }
  
  
    // 私有方法
    private getBirthYear( currentYear:number): number {
      return  currentYear - this.age;
    }
  }
  