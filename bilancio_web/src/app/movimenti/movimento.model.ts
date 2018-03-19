export class Movimento {
    id: number;
    type: string;
    description: string;
    amount: number;
    data_movimento: Date;
    categoria_id: Number;

    constructor( json_o: Object){
        this.amount = json_o["amount"];
        this.type = json_o["type"];
        this.description = json_o["description"];
        this.data_movimento = json_o["date"];
        this.categoria_id = json_o["categoria_id"];
        this.id = json_o["id"][0];
        
    }

    getAbsAmount() {
        return Math.abs(this.amount);
    }
}