namespace Shop.Application.Features.Orders;

/// <summary>Moves an order to a settable state.</summary>
/// <param name="OrderNumber">The order to move.</param>
/// <param name="State">The state to set.</param>
/// <param name="Note">A note to store with the order; omitted, the stored one is cleared.</param>
public sealed record SetOrderStateCommand(string OrderNumber, SettableOrderState State, string? Note);
