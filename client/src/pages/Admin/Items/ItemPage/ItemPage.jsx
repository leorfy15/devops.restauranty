import { useState, useEffect } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";

const url = process.env.REACT_APP_SERVER_URL || window.location.origin;

function ItemsPage() {

    const [item, setItem] = useState("");

    const { itemId } = useParams();

    useEffect(() => {
        axios.get(`${url}/api/items/items/${itemId}`).then((response) => {
            setItem(response.data);
            console.log(response.data);
        });
    }, []);
    return (
        <div>
            <img src={item.image} width={400} className="images"></img>
            <h1>{item.name}</h1>
            <h1>{item.price}</h1>
            <h1>{item.description}</h1>
            <h1>{item.dietaryInformation}</h1>
            {item.availability === true ? <h1>available</h1> : <h1>not available</h1>}



        </div >
    );
}

export default ItemsPage;
